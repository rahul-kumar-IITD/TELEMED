import { AriaLiveRegion } from "./AriaLiveRegion";

interface Props {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: Props) {
  return (
    <AriaLiveRegion assertive>
      <div data-testid="error-state" className="msg msg-err">
        {message}
        {onRetry ? (
          <button type="button" className="btn btn-sec ml-2" onClick={onRetry}>
            Retry
          </button>
        ) : null}
      </div>
    </AriaLiveRegion>
  );
}
