export interface BankSampah {
  id: number;
  name: string;
  city: string | null;
  is_demo: boolean;
}

export interface User {
  id: number;
  username: string;
  bank_sampah: BankSampah | null;
}

export interface LoginCredentials {
  username: string;
  password: string;
}
