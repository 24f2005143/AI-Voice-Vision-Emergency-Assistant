import { DEV_MOCK_RESULTS } from "../devMocks";

/**
 * DEVELOPMENT ONLY. App.jsx renders this behind `import.meta.env.DEV`, so it
 * is removed from production builds. It sets result state directly and makes
 * no network call — it is not a stand-in backend.
 */
export default function DevPanel({ onSelect, onError, onReset }) {
  return (
    <section className="dev-panel">

      <p className="dev-panel__note">
        Development only — sample states for visual checking while the backend
        is not implemented. No network call is made.
      </p>

      <div className="dev-panel__buttons">
        {DEV_MOCK_RESULTS.map((mock) => (
          <button key={mock.label} type="button" onClick={() => onSelect(mock.result)}>
            {mock.label}
          </button>
        ))}

        <button type="button" onClick={onError}>
          Error state
        </button>

        <button type="button" onClick={onReset}>
          Reset
        </button>
      </div>

    </section>
  );
}
