/* Minimalist inline-SVG icon set (replaces lucide-react). Consistent 1.8 stroke,
   currentColor, sized via the `size` prop. */
function Svg({ size = 20, children, ...rest }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...rest}>
      {children}
    </svg>
  );
}

export const Cpu = (p) => <Svg {...p}><rect x="6" y="6" width="12" height="12" rx="2" /><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2" /></Svg>;
export const Zap = (p) => <Svg {...p}><path d="M13 2 4 14h7l-1 8 9-12h-7l1-8z" /></Svg>;
export const ShieldAlert = (p) => <Svg {...p}><path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" /><path d="M12 8v4M12 16h.01" /></Svg>;
export const BarChart3 = (p) => <Svg {...p}><path d="M4 20V10M10 20V4M16 20v-8M22 20H2" /></Svg>;
export const Activity = (p) => <Svg {...p}><path d="M22 12h-4l-3 8-4-16-3 8H2" /></Svg>;
export const Globe = (p) => <Svg {...p}><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c2.5 2.5 2.5 15 0 18M12 3c-2.5 2.5-2.5 15 0 18" /></Svg>;
export const Lightbulb = (p) => <Svg {...p}><path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10.5c.8.8 1 1.5 1 2.5h6c0-1 .2-1.7 1-2.5A6 6 0 0 0 12 3z" /></Svg>;
export const TrendingDown = (p) => <Svg {...p}><path d="M22 17 13.5 8.5l-5 5L2 7" /><path d="M16 17h6v-6" /></Svg>;
export const Star = (p) => <Svg {...p}><path d="M12 3l2.9 5.9 6.5.9-4.7 4.6 1.1 6.5-5.8-3-5.8 3 1.1-6.5L2.6 9.8l6.5-.9L12 3z" /></Svg>;
export const ChevronDown = (p) => <Svg {...p}><path d="m6 9 6 6 6-6" /></Svg>;
export const ChevronUp = (p) => <Svg {...p}><path d="m6 15 6-6 6 6" /></Svg>;
export const CheckCircle = (p) => <Svg {...p}><circle cx="12" cy="12" r="9" /><path d="m8 12 3 3 5-6" /></Svg>;
export const Mail = (p) => <Svg {...p}><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" /></Svg>;
export const MapPin = (p) => <Svg {...p}><path d="M12 21s7-5.5 7-11a7 7 0 1 0-14 0c0 5.5 7 11 7 11z" /><circle cx="12" cy="10" r="2.5" /></Svg>;
export const Phone = (p) => <Svg {...p}><path d="M5 3h4l2 5-2.5 1.5a11 11 0 0 0 5 5L20 12l1 4v3a1 1 0 0 1-1 1 16 16 0 0 1-15-15 1 1 0 0 1 1-1z" /></Svg>;
