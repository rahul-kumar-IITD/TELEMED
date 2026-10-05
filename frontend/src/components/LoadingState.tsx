export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div data-testid="loading-state" aria-busy="true">
      <p className="text-ink2 text-sm m-0">{label}</p>
      <div className="skel" />
      <div className="skel w-3/5" />
    </div>
  );
}
