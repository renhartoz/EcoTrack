export interface BankSampah {
  id: string;
  name: string;
  city: string | null;
  is_demo: boolean;
}

export interface User {
  id: string;
  username: string;
  bank_sampah: BankSampah | null;
}

export interface LoginCredentials {
  username: string;
  password: string;
}
