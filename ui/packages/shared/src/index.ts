export interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  is_admin: boolean;
}

export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}
