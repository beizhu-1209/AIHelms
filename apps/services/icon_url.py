import re

from core.config import settings
from exceptions import ValidationError


def _pascal_to_kebab(name: str) -> str:
    with_word_breaks = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", name)
    with_number_breaks = re.sub(r"([A-Za-z])([0-9])", r"\1-\2", with_word_breaks)
    return with_number_breaks.lower()


_PROVIDER_ICON_FILES = {
    "openai": "openai.svg",
    "anthropic": "anthropic.svg",
    "azure": "azure.svg",
    "google": "google.svg",
    "deepseek": "deepseek.svg",
    "bedrock": "bedrock.svg",
    "vertex_ai": "vertex_ai.svg",
    "volcengine": "volcengine.png",
    "dashscope": "dashscope.png",
    "zhipu": "zhipu.svg",
    "moonshot": "moonshot.svg",
    "minimax": "minimax.svg",
    "xiaomi_mimo": "xiaomi_mimo.png",
    "vllm": "vllm.png",
    "sglang": "sglang.png",
    "ollama": "ollama.svg",
    "lmstudio": "lmstudio.svg",
    "xai": "xai.svg",
    "tencent": "tencent.png",
    "openai_compatible": "openai_compatible.svg",
    "custom": "custom.svg",
    "other": "custom.svg",
}

_LUCIDE_ICON_NAMES = {
    "Search",
    "Code",
    "FileText",
    "Database",
    "Globe",
    "Bot",
    "Brain",
    "Sparkles",
    "Zap",
    "Shield",
    "Lock",
    "Key",
    "Eye",
    "MessageSquare",
    "Send",
    "Upload",
    "Download",
    "FolderOpen",
    "File",
    "FileCode",
    "Terminal",
    "Server",
    "Cloud",
    "Wifi",
    "Link",
    "GitBranch",
    "GitPullRequest",
    "Package",
    "Box",
    "Layers",
    "BarChart3",
    "LineChart",
    "PieChart",
    "TrendingUp",
    "Activity",
    "Users",
    "UserCheck",
    "Building2",
    "Briefcase",
    "Wallet",
    "CreditCard",
    "DollarSign",
    "Calculator",
    "ClipboardList",
    "CheckSquare",
    "AlertTriangle",
    "Info",
    "HelpCircle",
    "Settings",
    "Wrench",
    "Hammer",
    "Puzzle",
    "Lightbulb",
    "Rocket",
    "Target",
    "Flag",
    "Bookmark",
    "Star",
    "Heart",
    "ThumbsUp",
    "Languages",
    "BookOpen",
    "GraduationCap",
    "Microscope",
    "FlaskConical",
    "Cpu",
    "HardDrive",
    "Monitor",
    "Smartphone",
    "Tablet",
    "Camera",
    "Image",
    "Video",
    "Music",
    "Headphones",
    "Mail",
    "Bell",
    "Calendar",
    "Clock",
    "Timer",
    "MapPin",
    "Navigation",
    "Compass",
    "Map",
    "Route",
    "Scissors",
    "Pen",
    "Paintbrush",
    "Palette",
    "Wand2",
    "Presentation",
    "Network",
    "SpellCheck",
    "Code2",
    "PenLine",
    "ShoppingCart",
}

_EMOJI_ICON_FILES = {"📦": "package.svg", "🤖": "bot.svg"}
_LUCIDE_ICON_FILES = {f"{_pascal_to_kebab(name)}.svg" for name in _LUCIDE_ICON_NAMES}
_HOSTED_ICON_PATH = re.compile(
    r"^/icons/v1/(?:default\.svg|(?:lucide|providers)/[a-z0-9][a-z0-9_-]*\.(?:svg|png))$"
)


def _base_url() -> str:
    return settings.platform_public_url.rstrip("/")


def _default_url() -> str:
    return f"{_base_url()}/icons/v1/default.svg"


def normalize_hosted_icon_path(raw: str | None) -> str | None:
    if not raw or not raw.strip():
        return None

    value = raw.strip()
    absolute_prefix = f"{_base_url()}/icons/"
    if value.startswith(absolute_prefix):
        value = value[len(_base_url()) :]

    if not _HOSTED_ICON_PATH.fullmatch(value):
        raise ValidationError("图标必须使用平台内置图标地址")
    return value


def resolve_icon_url(raw: str | None) -> str:
    if not raw or not raw.strip():
        return _default_url()

    value = raw.strip()
    if value.startswith(("http://", "https://")):
        return value
    if value.startswith("/icons/"):
        return f"{_base_url()}{value}"
    if value in _EMOJI_ICON_FILES:
        filename = _EMOJI_ICON_FILES[value]
    elif value in _LUCIDE_ICON_NAMES:
        filename = f"{_pascal_to_kebab(value)}.svg"
    elif value.lower() in _LUCIDE_ICON_FILES:
        filename = value.lower()
    else:
        return _default_url()
    return f"{_base_url()}/icons/v1/lucide/{filename}"


def resolve_provider_icon_url(provider_type: str | None) -> str:
    filename = _PROVIDER_ICON_FILES.get((provider_type or "").lower())
    if not filename:
        return _default_url()
    return f"{_base_url()}/icons/v1/providers/{filename}"
