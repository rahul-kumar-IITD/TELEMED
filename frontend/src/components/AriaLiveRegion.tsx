import type { ReactNode } from "react";

interface Props {
  children?: ReactNode;
  /** Use for errors: role="alert" (assertive). Default is a polite status region. */
  assertive?: boolean;
  id?: string;
  className?: string;
}

/** Always rendered so the live region exists in the DOM before a message is inserted. */
export function AriaLiveRegion({ children, assertive = false, id, className }: Props) {
  return (
    <div
      id={id}
      role={assertive ? "alert" : "status"}
      aria-live={assertive ? "assertive" : "polite"}
      className={className}
    >
      {children}
    </div>
  );
}
