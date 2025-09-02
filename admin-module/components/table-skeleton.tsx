interface TableSkeletonProps {
  columns: number;
  rows?: number;
  widths?: (string | number)[];
}

export default function TableSkeleton({
  columns,
  rows = 5,
  widths,
}: TableSkeletonProps) {
  const defaultWidths = ["w-32", "w-48", "w-16", "w-20", "w-24"];

  function SkeletonRow({ index }: { index: number }) {
    return (
      <tr className="border-b border-border">
        {Array.from({ length: columns }).map((_, i) => (
          <td key={i} className="py-3 px-6">
            <div
              className={`h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse ${
                widths?.[i] || defaultWidths[i] || "w-24"
              }`}
              style={{
                animationDelay: `${(index * columns + i) * 0.05}s`,
              }}
            />
          </td>
        ))}
      </tr>
    );
  }

  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonRow key={`skeleton-${i}`} index={i} />
      ))}
    </>
  );
}
