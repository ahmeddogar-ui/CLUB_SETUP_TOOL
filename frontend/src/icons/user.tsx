import type { IconProps } from ".";

export function UserIcon(props: IconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={24}
      height={24}
      viewBox="0 0 24 24"
      fill="none"
      {...props}
    >
      <circle cx={12} cy={8} r={3.75} stroke="currentColor" strokeWidth={1.5} />
      <path
        d="M4.75 19.25a7.25 7.25 0 0114.5 0"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinecap="round"
      />
    </svg>
  );
}
