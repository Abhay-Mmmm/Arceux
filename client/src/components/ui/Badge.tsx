import React from 'react';
import { cn } from '../../lib/utils';

type Variant = 'default' | 'secondary' | 'destructive' | 'outline' | 'ghost' | 'critical' | 'high' | 'medium' | 'low' | 'healthy' | 'degraded' | 'down';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    variant?: Variant;
}

export const Badge: React.FC<BadgeProps> = ({
    className,
    variant = 'default',
    ...props
}) => {
    const variants: Record<string, string> = {
        default: "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",

        // Severity / Status specific (Custom)
        critical: "border-transparent bg-red-500/15 text-red-500 hover:bg-red-500/25 border-red-500/20",
        high: "border-transparent bg-orange-500/15 text-orange-500 hover:bg-orange-500/25 border-orange-500/20",
        medium: "border-transparent bg-yellow-500/15 text-yellow-500 hover:bg-yellow-500/25 border-yellow-500/20",
        low: "border-transparent bg-blue-500/15 text-blue-500 hover:bg-blue-500/25 border-blue-500/20",

        healthy: "border-transparent bg-green-500/15 text-green-500 hover:bg-green-500/25 border-green-500/20 shadow-[0_0_10px_-4px_rgba(34,197,94,0.5)]",
        degraded: "border-transparent bg-yellow-500/15 text-yellow-500 hover:bg-yellow-500/25 border-yellow-500/20",
        down: "border-transparent bg-red-500/15 text-red-500 hover:bg-red-500/25 border-red-500/20",
    };

    return (
        <div className={cn(
            "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
            variants[variant] || variants.default,
            className
        )} {...props} />
    );
};
