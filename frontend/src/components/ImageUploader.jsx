import { useEffect, useRef, useState } from "react";

/**
 * Framed as "add a photo", not "upload visual input". The user is providing
 * evidence of what they can see, not operating a file transfer tool.
 */
export default function ImageUploader({ onImageReady, disabled }) {
  const [previewUrl, setPreviewUrl] = useState("");
  const [fileName, setFileName] = useState("");

  const inputRef = useRef(null);
  const previewUrlRef = useRef("");

  function revokePreview() {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = "";
    }
  }

  useEffect(() => revokePreview, []);


  function handleChange(event) {
    const file = event.target.files?.[0];

    revokePreview();

    if (!file) {
      setPreviewUrl("");
      setFileName("");
      onImageReady(null);

      return;
    }

    const url = URL.createObjectURL(file);

    previewUrlRef.current = url;
    setPreviewUrl(url);
    setFileName(file.name);
    onImageReady(file);
  }


  function handleClear() {
    revokePreview();
    setPreviewUrl("");
    setFileName("");
    onImageReady(null);

    // Resetting the input lets the same file be picked again afterwards.
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }


  function openPicker() {
    inputRef.current?.click();
  }


  return (
    <section className="panel panel--image" aria-labelledby="image-heading">

      <h2 id="image-heading" className="panel__title">Add a photo</h2>

      {/* Visually hidden, but still the real, keyboard-reachable control. */}
      <input
        ref={inputRef}
        id="image-input"
        className="visually-hidden"
        type="file"
        accept="image/*"
        onChange={handleChange}
        disabled={disabled}
      />

      {!previewUrl && (
        <button
          type="button"
          className="photo-button"
          onClick={openPicker}
          disabled={disabled}
        >
          <span className="photo-button__glyph" aria-hidden="true">▢</span>

          <span className="photo-button__label">Choose a photo</span>
        </button>
      )}

      {previewUrl && (
        <>
          <img
            className="photo-preview"
            src={previewUrl}
            alt={fileName ? `Selected photo: ${fileName}` : "Selected photo"}
          />

          <div className="photo-actions">
            <button type="button" className="text-button" onClick={openPicker}>
              Replace
            </button>

            <button type="button" className="text-button" onClick={handleClear}>
              Remove
            </button>
          </div>
        </>
      )}

      {!previewUrl && (
        <p className="panel__hint">Optional. Voice alone is enough.</p>
      )}

    </section>
  );
}
