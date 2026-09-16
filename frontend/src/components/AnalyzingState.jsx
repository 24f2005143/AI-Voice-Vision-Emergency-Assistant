import { useEffect, useState } from "react";

/**
 * An unexplained spinner tells a frightened person nothing except that they
 * are waiting. These lines name what is actually being done, and they are
 * built from what the user really submitted, so the interface never claims to
 * be checking an image that was never provided.
 *
 * There is no progress percentage: the request has no measurable progress and
 * inventing one would be a lie.
 */
function buildSteps(sources) {
  const steps = [];

  if (sources.voice) {
    steps.push("Listening to your description");
  }

  if (sources.text && !sources.voice) {
    steps.push("Reading your description");
  }

  if (sources.image) {
    steps.push("Checking the photo");
  }

  if ((sources.voice || sources.text) && sources.image) {
    steps.push("Combining both signals");
  }

  return steps.length ? steps : ["Working through what you sent"];
}


export default function AnalyzingState({ sources }) {
  const steps = buildSteps(sources);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (steps.length < 2) {
      return undefined;
    }

    const timer = setInterval(() => {
      setIndex((value) => (value + 1) % steps.length);
    }, 1400);

    return () => clearInterval(timer);
  }, [steps.length]);

  return (
    <section className="analyzing" role="status" aria-live="polite">

      <div className="analyzing__bar" aria-hidden="true">
        <span className="analyzing__bar-fill" />
      </div>

      <p className="analyzing__title">Analyzing the situation…</p>

      <p className="analyzing__step">{steps[index] || steps[0]}</p>

    </section>
  );
}
