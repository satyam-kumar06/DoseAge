/* A pill strip drawing per medicine.
 *
 * Parents recognise "the blue strip" long before they read a brand name. When
 * the family has photographed the actual strip we show the photo; until then
 * we draw a strip whose colour and shape are derived from the medicine name,
 * so the same medicine always looks the same on every screen.
 */
const PALETTE = [
  ["#0F766E", "#CFE9E5"],
  ["#2F3A73", "#DDE2F5"],
  ["#8A4B14", "#FDE4CE"],
  ["#7A5B10", "#FDF3D0"],
  ["#7A1F4B", "#F7D9E6"],
  ["#1F5B2E", "#D6EFDC"],
  ["#4B3A73", "#E4DDF5"],
];

function hash(text = "") {
  let h = 0;
  for (let i = 0; i < text.length; i += 1) h = (h * 31 + text.charCodeAt(i)) >>> 0;
  return h;
}

export default function PillArt({ brand = "", form = "tablet", photoUrl, size = 72, className = "" }) {
  if (photoUrl) {
    return (
      <img
        src={photoUrl}
        alt=""
        width={size}
        height={size}
        className={`rounded-xl object-cover ${className}`}
      />
    );
  }

  const h = hash(brand);
  const [ink, bg] = PALETTE[h % PALETTE.length];
  const round = form === "capsule" ? 14 : 10;
  const capsule = form === "capsule";

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 72 72"
      className={className}
      role="img"
      aria-label={brand ? `${brand} strip` : "medicine strip"}
    >
      <rect x="2" y="2" width="68" height="68" rx="16" fill={bg} />
      <g>
        {[0, 1].map((row) =>
          [0, 1].map((col) => {
            const x = 14 + col * 24;
            const y = 14 + row * 24;
            return capsule ? (
              <g key={`${row}-${col}`}>
                <rect x={x} y={y + 6} width="20" height="14" rx="7" fill="#fff" />
                <path d={`M${x + 10} ${y + 6}h3a7 7 0 0 1 0 14h-3z`} fill={ink} />
                <rect x={x} y={y + 6} width="20" height="14" rx="7" fill="none" stroke={ink} strokeWidth="1.5" />
              </g>
            ) : (
              <g key={`${row}-${col}`}>
                <rect x={x} y={y + 4} width="20" height="18" rx={round} fill="#fff" stroke={ink} strokeWidth="1.5" />
                <line x1={x + 10} y1={y + 7} x2={x + 10} y2={y + 19} stroke={ink} strokeWidth="1.5" opacity=".5" />
              </g>
            );
          })
        )}
      </g>
    </svg>
  );
}
