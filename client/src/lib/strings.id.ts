export const ROUTE_LABELS = {
  auto: "Tersimpan otomatis",
  confirm: "Perlu konfirmasi",
  manual: "Perlu diisi",
} as const;

export type RouteType = keyof typeof ROUTE_LABELS;

export const FLAG_MESSAGES = {
  WEIGHT_UNPARSEABLE: "Berat tidak terbaca",
  WEIGHT_NONPOSITIVE: "Berat tidak valid",
  WEIGHT_OUT_OF_RANGE: "Berat tidak lazim, periksa kembali",
  TYPE_UNKNOWN: "Jenis sampah tidak dikenali",
  AMBIGUOUS_TYPE: "Jenis sampah bisa lebih dari satu",
  NASABAH_UNKNOWN: "Nama belum terdaftar",
  AMBIGUOUS_NASABAH: "Nama mirip dengan beberapa nasabah",
  DATE_UNPARSEABLE: "Tanggal tidak terbaca",
  DATE_OUT_OF_RANGE: "Tanggal di luar rentang wajar",
  DATE_INHERITED: "Tanggal mengikuti baris sebelumnya",
  UNIT_ASSUMED_KG: "Satuan tidak tertulis, dianggap kg",
  LOW_LLM_CONFIDENCE: "Tulisan sulit dibaca",
  ILLEGIBLE_FIELD: "Ada kolom yang tidak terbaca",
  DUPLICATE_IN_PAGE: "Kemungkinan baris ganda di halaman ini",
  DUPLICATE_IN_DB: "Setoran serupa sudah tercatat",
  PAGE_TOTAL_MISMATCH: "Total halaman tidak cocok dengan jumlah baris",
  WEIGHT_READER_MISMATCH: "Dua pembacaan berat berbeda",
} as const;

export type FlagCode = keyof typeof FLAG_MESSAGES;

export const ERROR_MESSAGES = {
  UNAUTHENTICATED: "Sesi telah berakhir atau tidak valid",
  NOT_FOUND: "Data tidak ditemukan",
  VALIDATION_ERROR: "Format data tidak valid",
  INVALID_IMAGE: "Berkas gambar tidak valid",
  FILE_TOO_LARGE: "Ukuran berkas melebihi batas",
  THROTTLED: "Terlalu banyak permintaan, coba lagi nanti",
  ROW_NOT_PENDING: "Baris sudah diproses sebelumnya",
  ROW_HAS_HARD_FLAGS: "Baris memiliki kesalahan yang harus diperbaiki",
  LLM_TIMEOUT: "Batas waktu pemrosesan habis",
  LLM_API_ERROR: "Terjadi gangguan pada layanan pemrosesan",
  LLM_SCHEMA_INVALID: "Format pembacaan tidak sesuai",
  REPLAY_MISS: "Data replay tidak ditemukan",
  LLM_RATE_LIMITED: "Layanan sedang sibuk. Coba lagi dalam 1 menit.",
  OCR_API_ERROR: "Gangguan pada pembacaan teks OCR",
  CSRF_FAILED: "Permintaan ditolak karena token keamanan tidak valid",
} as const;

export type ErrorCode = keyof typeof ERROR_MESSAGES;

export const UI_STRINGS = {
  appTitle: "EcoTrack",
  loginTitle: "Masuk ke EcoTrack",
  loginSubtitle: "Kelola setoran bank sampah dengan cepat dan akurat",
  usernameLabel: "Nama pengguna",
  passwordLabel: "Kata sandi",
  loginButton: "Masuk",
  loggingInButton: "Memproses...",
  logoutButton: "Keluar",
  navDashboard: "Beranda",
  navUpload: "Unggah",
  navHistory: "Riwayat",
  navDeposits: "Setoran",
  navNasabah: "Nasabah",
  navReports: "Laporan",
  loading: "Memuat...",
  sessionChecking: "Memeriksa sesi...",
  unknownError: "Terjadi kesalahan yang tidak diharapkan",
} as const;
