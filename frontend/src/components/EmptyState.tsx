export function EmptyState({ message = "Nothing here yet." }: { message?: string }) {
  return (
    <div
      data-testid="empty-state"
      className="text-center py-8 px-3 text-ink2 border-2 border-dashed border-line rounded-[10px]"
    >
      {message}
    </div>
  );
}
