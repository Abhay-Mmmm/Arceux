import React from 'react';
import { cn } from '../../lib/utils';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
    title?: string;
    description?: string;
    action?: React.ReactNode;
    noPadding?: boolean;
}

export const Card: React.FC<CardProps> = ({
    title,
    description,
    action,
    children,
    className,
    noPadding = false,
    ...props
}) => {
    return (
        <div
            className={cn(
                "rounded-xl border border-border bg-card text-card-foreground shadow-sm flex flex-col overflow-hidden",
                className
            )}
            {...props}
        >
            {(title || action) && (
                <div className="flex flex-col space-y-1.5 p-6 pb-4">
                    <div className="flex items-center justify-between">
                        {title && <h3 className="font-semibold leading-none tracking-tight">{title}</h3>}
                        {action && <div>{action}</div>}
                    </div>
                    {description && <p className="text-sm text-muted-foreground">{description}</p>}
                </div>
            )}
            <div className={cn("flex-1 flex flex-col min-h-0", noPadding ? "p-0" : "p-6 pt-0")}>
                {children}
            </div>
        </div>
    );
};
