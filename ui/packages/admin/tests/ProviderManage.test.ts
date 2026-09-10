import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { App } from 'vue'
import {
  deleteCredential, deleteProvider, getCredentials, getProviders,
  type Credential, type Provider,
} from '@aihelms/shared'
import ProviderManage from '../src/views/providers/ProviderManage.vue'
import {
  clickNode, createNode, findNode, flushUpdates, nodeText, renderer,
  type RenderNode,
} from './inMemoryVueRenderer'

vi.mock('@aihelms/shared', () => ({
  getProviders: vi.fn(), createProvider: vi.fn(), updateProvider: vi.fn(),
  deleteProvider: vi.fn(), getCredentials: vi.fn(), createCredential: vi.fn(),
  updateCredential: vi.fn(), deleteCredential: vi.fn(), getCredentialModels: vi.fn(),
  getProviderModels: vi.fn(), usePermission: () => ({ hasPermission: () => true }),
}))
vi.mock('../src/components/AccessTestDialog.vue', () => ({ default: { render: () => null } }))
vi.mock('../src/components/ProviderIcon.vue', () => ({ default: { render: () => null } }))

const provider: Provider = {
  id: 42, name: '测试供应商', provider_type: 'openai', billing_type: 'token',
  monthly_budget: null, monthly_used: '0', is_active: true, description: '',
  config: {}, credential_count: 1, created_at: null, updated_at: null,
}
const credential: Credential = {
  id: 84, credential_name: '测试凭证', provider_id: provider.id,
  provider_name: provider.name, provider_type: provider.provider_type,
  credential_values: {}, credential_info: {}, litellm_synced: true,
  is_active: true, deployment_count: 1, created_at: null, updated_at: null,
}
const credentialConflict = '该凭证被部署引用，请先解除关联'
const providerConflict = '该供应商下有凭证，请先删除或迁移凭证'

describe('ProviderManage deletion feedback', () => {
  let root: RenderNode
  let app: App

  function getNode(matches: (node: RenderNode) => boolean): RenderNode {
    const node = findNode(root, matches)
    if (!node) throw new Error('Expected rendered node was not found')
    return node
  }

  function button(label: string): RenderNode {
    return getNode(node => node.tag === 'button' && nodeText(node) === label)
  }

  function dialog(): RenderNode | undefined {
    return findNode(root, node => node.props.role === 'dialog')
  }

  async function openDelete(kind: 'provider' | 'credential'): Promise<void> {
    await clickNode(getNode(node => node.props['data-testid'] === `delete-${kind}-button`))
    expect(dialog()).toBeDefined()
  }

  beforeEach(async () => {
    vi.resetAllMocks()
    vi.mocked(getProviders).mockResolvedValue({ items: [provider], total: 1, page: 1, page_size: 100 })
    vi.mocked(getCredentials).mockResolvedValue({ items: [credential], total: 1, page: 1, page_size: 100 })
    vi.mocked(deleteProvider).mockResolvedValue(null)
    vi.mocked(deleteCredential).mockResolvedValue(null)
    root = createNode('root')
    app = renderer.createApp(ProviderManage)
    app.mount(root)
    await flushUpdates()
    await clickNode(getNode(node => node.tag === 'div' && typeof node.props.onClick === 'function'
      && nodeText(node).includes(provider.name)))
  })

  afterEach(() => app.unmount())

  it('should keep the credential dialog open and show the exact conflict reason', async () => {
    vi.mocked(deleteCredential).mockRejectedValueOnce(new Error(credentialConflict))
    await openDelete('credential')
    await clickNode(button('确认'))
    expect(dialog()).toBeDefined()
    expect(nodeText(getNode(node => node.props.role === 'alert'))).toBe(credentialConflict)
    expect(findNode(root, node => node.props['data-testid'] === 'delete-credential-button')).toBeDefined()
    expect(getCredentials).toHaveBeenCalledTimes(1)
  })

  it('should keep the provider dialog open and show its conflict reason', async () => {
    vi.mocked(deleteProvider).mockRejectedValueOnce(new Error(providerConflict))
    await openDelete('provider')
    await clickNode(button('确认'))
    expect(dialog()).toBeDefined()
    expect(nodeText(getNode(node => node.props.role === 'alert'))).toBe(providerConflict)
    expect(getProviders).toHaveBeenCalledTimes(1)
  })

  it('should close after credential deletion succeeds and refresh the credential and provider lists', async () => {
    await openDelete('credential')
    vi.mocked(getCredentials).mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 100 })
    await clickNode(button('确认'))
    expect(dialog()).toBeUndefined()
    expect(deleteCredential).toHaveBeenCalledWith(credential.id)
    expect(findNode(root, node => node.props['data-testid'] === 'delete-credential-button')).toBeUndefined()
    expect(getProviders).toHaveBeenCalledTimes(2)
  })

  it('should close after provider deletion succeeds and clear the selected provider', async () => {
    await openDelete('provider')
    vi.mocked(getProviders).mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 100 })
    await clickNode(button('确认'))
    expect(dialog()).toBeUndefined()
    expect(deleteProvider).toHaveBeenCalledWith(provider.id)
    expect(findNode(root, node => node.props['data-testid'] === 'delete-provider-button')).toBeUndefined()
  })

  it('should clear an old error when canceling and reopening deletion', async () => {
    vi.mocked(deleteCredential).mockRejectedValueOnce(new Error(credentialConflict))
    await openDelete('credential')
    await clickNode(button('确认'))
    await clickNode(button('取消'))
    expect(dialog()).toBeUndefined()
    await openDelete('credential')
    expect(findNode(root, node => node.props.role === 'alert')).toBeUndefined()
    expect(deleteCredential).toHaveBeenCalledTimes(1)
  })

  it('should allow retry after a conflict and close only when the retry succeeds', async () => {
    vi.mocked(deleteProvider).mockRejectedValueOnce(new Error(providerConflict))
    await openDelete('provider')
    await clickNode(button('确认'))
    expect(dialog()).toBeDefined()
    await clickNode(button('确认'))
    expect(dialog()).toBeUndefined()
    expect(deleteProvider).toHaveBeenCalledTimes(2)
  })

  it('should show progress and prevent repeat actions while deletion is pending', async () => {
    let finish: (value: null) => void = () => { throw new Error('Pending request not initialized') }
    vi.mocked(deleteCredential).mockReturnValueOnce(new Promise(resolve => { finish = resolve }))
    await openDelete('credential')
    await clickNode(button('确认'))
    expect(button('处理中...').props.disabled).toBe(true)
    expect(button('取消').props.disabled).toBe(true)
    await clickNode(button('处理中...'))
    expect(deleteCredential).toHaveBeenCalledTimes(1)
    finish(null)
    await flushUpdates()
    expect(dialog()).toBeUndefined()
  })

  it('should close on cancel without sending a delete request', async () => {
    await openDelete('provider')
    await clickNode(button('取消'))
    expect(dialog()).toBeUndefined()
    expect(deleteProvider).not.toHaveBeenCalled()
    expect(deleteCredential).not.toHaveBeenCalled()
  })
})
