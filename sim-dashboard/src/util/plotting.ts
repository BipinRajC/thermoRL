export function unpack(rows: { [key: string]: string }[], key: string) {
  return rows.map(row => row[key]);
}
