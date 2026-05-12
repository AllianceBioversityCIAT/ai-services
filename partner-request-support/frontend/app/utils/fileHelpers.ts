export const downloadFile = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const filterPartners = <T extends { name: string; acronym?: string }>(
  items: T[] | undefined | null,
  query: string
): T[] => {
  if (!items) return [];
  const lowerQuery = query.toLowerCase();
  return items.filter(
    (item) =>
      item.name.toLowerCase().includes(lowerQuery) ||
      item.acronym?.toLowerCase().includes(lowerQuery)
  );
};
