import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { useNavigate } from "react-router";
import {
  Camera,
  CheckCircle2,
  FileText,
  Image as ImageIcon,
  RotateCw,
  UploadCloud,
} from "lucide-react";
import { computeSha256Hex, resizeImageToJpeg } from "@/lib/image";
import { ERROR_MESSAGES, UI_STRINGS, type ErrorCode } from "@/lib/strings.id";
import {
  createImageUpload,
  createTextUpload,
  retryUpload,
} from "@/services/uploads";
import { ApiError } from "@/types/api";

export function UploadPage() {
  const navigate = useNavigate();

  const cameraInputRef = useRef<HTMLInputElement>(null);
  const galleryInputRef = useRef<HTMLInputElement>(null);

  const [activeTab, setActiveTab] = useState<"photo" | "text">("photo");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [textInput, setTextInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [failedUploadId, setFailedUploadId] = useState<number | null>(null);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setErrorMessage(null);
    setFailedUploadId(null);
    setSelectedFile(file);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(URL.createObjectURL(file));
  }

  async function handlePhotoUpload() {
    if (!selectedFile || isProcessing) {
      return;
    }

    setIsProcessing(true);
    setErrorMessage(null);
    setFailedUploadId(null);

    try {
      const sourceSha256 = await computeSha256Hex(selectedFile);
      const resizedJpegBlob = await resizeImageToJpeg(selectedFile);
      const result = await createImageUpload(
        resizedJpegBlob,
        sourceSha256,
        selectedFile.name || "ledger.jpg",
      );

      if (result.status === "failed") {
        setFailedUploadId(result.id);
        if (result.error_code === "LLM_RATE_LIMITED") {
          setErrorMessage(ERROR_MESSAGES.LLM_RATE_LIMITED);
        } else {
          setErrorMessage(
            result.error_message ||
              (result.error_code
                ? ERROR_MESSAGES[result.error_code as ErrorCode]
                : UI_STRINGS.unknownError),
          );
        }
        return;
      }

      navigate(`/uploads/${result.id}`);
    } catch (error) {
      if (error instanceof ApiError) {
        const mapped = ERROR_MESSAGES[error.code as ErrorCode];
        setErrorMessage(mapped || error.message || UI_STRINGS.unknownError);
      } else {
        setErrorMessage(UI_STRINGS.unknownError);
      }
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleTextSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!textInput.trim() || isProcessing) {
      return;
    }

    setIsProcessing(true);
    setErrorMessage(null);
    setFailedUploadId(null);

    try {
      const result = await createTextUpload(textInput);
      if (result.status === "failed") {
        setFailedUploadId(result.id);
        if (result.error_code === "LLM_RATE_LIMITED") {
          setErrorMessage(ERROR_MESSAGES.LLM_RATE_LIMITED);
        } else {
          setErrorMessage(
            result.error_message ||
              (result.error_code
                ? ERROR_MESSAGES[result.error_code as ErrorCode]
                : UI_STRINGS.unknownError),
          );
        }
        return;
      }
      navigate(`/uploads/${result.id}`);
    } catch (error) {
      if (error instanceof ApiError) {
        const mapped = ERROR_MESSAGES[error.code as ErrorCode];
        setErrorMessage(mapped || error.message || UI_STRINGS.unknownError);
      } else {
        setErrorMessage(UI_STRINGS.unknownError);
      }
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleRetry() {
    if (!failedUploadId || isProcessing) {
      return;
    }

    setIsProcessing(true);
    setErrorMessage(null);

    try {
      const result = await retryUpload(failedUploadId);
      if (result.status === "failed") {
        if (result.error_code === "LLM_RATE_LIMITED") {
          setErrorMessage(ERROR_MESSAGES.LLM_RATE_LIMITED);
        } else {
          setErrorMessage(
            result.error_message ||
              (result.error_code
                ? ERROR_MESSAGES[result.error_code as ErrorCode]
                : UI_STRINGS.unknownError),
          );
        }
        return;
      }
      navigate(`/uploads/${result.id}`);
    } catch (error) {
      if (error instanceof ApiError) {
        const mapped = ERROR_MESSAGES[error.code as ErrorCode];
        setErrorMessage(mapped || error.message || UI_STRINGS.unknownError);
      } else {
        setErrorMessage(UI_STRINGS.unknownError);
      }
    } finally {
      setIsProcessing(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="border-b border-rule pb-3">
        <h2 className="text-2xl font-bold tracking-tight text-ink">
          {UI_STRINGS.navUpload}
        </h2>
      </div>

      <div className="flex border-b border-rule" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "photo"}
          onClick={() => setActiveTab("photo")}
          disabled={isProcessing}
          className={`flex min-h-[44px] flex-1 items-center justify-center gap-2 border-b-2 font-medium text-sm transition-colors ${
            activeTab === "photo"
              ? "border-sprout text-sprout font-semibold"
              : "border-transparent text-muted-foreground hover:text-ink"
          }`}
        >
          <Camera className="h-4 w-4" />
          <span>{UI_STRINGS.tabPhoto}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "text"}
          onClick={() => setActiveTab("text")}
          disabled={isProcessing}
          className={`flex min-h-[44px] flex-1 items-center justify-center gap-2 border-b-2 font-medium text-sm transition-colors ${
            activeTab === "text"
              ? "border-sprout text-sprout font-semibold"
              : "border-transparent text-muted-foreground hover:text-ink"
          }`}
        >
          <FileText className="h-4 w-4" />
          <span>{UI_STRINGS.tabText}</span>
        </button>
      </div>

      {isProcessing && (
        <output
          aria-live="polite"
          className="flex items-center gap-3 rounded-sm border border-sprout/40 bg-sprout/10 p-4 text-sm font-medium text-sprout block"
        >
          <RotateCw className="h-5 w-5 animate-spin" />
          <span>{UI_STRINGS.uploadProcessing}</span>
        </output>
      )}

      {errorMessage && (
        <div
          role="alert"
          aria-live="polite"
          className="space-y-3 rounded-sm border border-brick bg-paper p-4 text-sm text-brick"
        >
          <p>{errorMessage}</p>
          {failedUploadId && (
            <button
              type="button"
              onClick={() => void handleRetry()}
              disabled={isProcessing}
              className="flex min-h-[44px] items-center gap-2 rounded-sm bg-brick px-4 py-2 font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              <RotateCw className="h-4 w-4" />
              <span>{UI_STRINGS.retryButton}</span>
            </button>
          )}
        </div>
      )}

      {activeTab === "photo" && (
        <div className="space-y-6">
          <div className="rounded-sm border border-rule bg-paper p-4">
            <h3 className="mb-3 font-semibold text-sm text-ink">
              {UI_STRINGS.photoGuideTitle}
            </h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-sprout" />
                <span>{UI_STRINGS.photoTip1}</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-sprout" />
                <span>{UI_STRINGS.photoTip2}</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-sprout" />
                <span>{UI_STRINGS.photoTip3}</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-sprout" />
                <span>{UI_STRINGS.photoTip4}</span>
              </li>
            </ul>
          </div>

          <input
            ref={cameraInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleFileChange}
            className="hidden"
          />
          <input
            ref={galleryInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="hidden"
          />

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <button
              type="button"
              disabled={isProcessing}
              onClick={() => cameraInputRef.current?.click()}
              className="flex min-h-[44px] items-center justify-center gap-2 rounded-sm bg-sprout px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Camera className="h-4 w-4" />
              <span>{UI_STRINGS.capturePhoto}</span>
            </button>
            <button
              type="button"
              disabled={isProcessing}
              onClick={() => galleryInputRef.current?.click()}
              className="flex min-h-[44px] items-center justify-center gap-2 rounded-sm border border-input-border bg-paper px-4 py-2 text-sm font-medium text-ink transition-colors hover:bg-muted/50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ImageIcon className="h-4 w-4" />
              <span>{UI_STRINGS.selectGallery}</span>
            </button>
          </div>

          {previewUrl && (
            <div className="space-y-4 rounded-sm border border-rule p-4">
              <div className="overflow-hidden rounded-sm border border-rule bg-muted/20">
                <img
                  src={previewUrl}
                  alt="Pratinjau berkas"
                  className="max-h-96 w-full object-contain"
                />
              </div>
              <button
                type="button"
                disabled={isProcessing}
                onClick={() => void handlePhotoUpload()}
                className="flex min-h-[44px] w-full items-center justify-center gap-2 rounded-sm bg-sprout px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <UploadCloud className="h-4 w-4" />
                <span>Mulai Proses Ekstraksi</span>
              </button>
            </div>
          )}
        </div>
      )}

      {activeTab === "text" && (
        <form onSubmit={handleTextSubmit} className="space-y-4">
          <div>
            <textarea
              rows={8}
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder={UI_STRINGS.textPlaceholder}
              disabled={isProcessing}
              className="w-full rounded-sm border border-input-border bg-paper p-3 font-mono text-sm text-ink outline-none focus-visible:ring-2 focus-visible:ring-sprout"
            />
          </div>
          <button
            type="submit"
            disabled={isProcessing || !textInput.trim()}
            className="flex min-h-[44px] w-full items-center justify-center gap-2 rounded-sm bg-sprout px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <FileText className="h-4 w-4" />
            <span>{UI_STRINGS.submitText}</span>
          </button>
        </form>
      )}
    </div>
  );
}
