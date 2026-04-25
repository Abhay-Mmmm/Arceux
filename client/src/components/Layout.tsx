import React, { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, AlertCircle, BrainCircuit, ShieldCheck, LogOut } from 'lucide-react';
import { cn } from '../lib/utils';


const Sidebar: React.FC = () => {
    const [showProfile, setShowProfile] = useState(false);
    const navItems = [
        { href: "/", label: "Dashboard", icon: LayoutDashboard },
        { href: "/alerts", label: "Alerts", icon: AlertCircle },
        { href: "/insights", label: "Agent Insights", icon: BrainCircuit },
    ];

    return (
        <aside className="w-16 border-r border-border bg-card flex flex-col shrink-0 h-full items-center py-4 z-50">
            <div className="mb-8">
                <div className="h-10 w-10 bg-primary/10 rounded-xl flex items-center justify-center text-primary ring-1 ring-primary/20">
                    <ShieldCheck className="h-6 w-6" />
                </div>
            </div>

            <nav className="flex flex-col gap-2 w-full px-2">
                {navItems.map((item) => (
                    <NavLink
                        key={item.href}
                        to={item.href}
                        className={({ isActive }) => cn(
                            "h-10 w-10 rounded-lg flex items-center justify-center transition-all duration-200",
                            isActive
                                ? "bg-primary text-primary-foreground shadow-md shadow-primary/20"
                                : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                        )}
                        title={item.label}
                    >
                        <item.icon className="h-5 w-5" />
                    </NavLink>
                ))}
            </nav>

            <div
                className="mt-auto flex flex-col gap-4 items-center w-full px-2 relative"
                onMouseEnter={() => setShowProfile(true)}
                onMouseLeave={() => setShowProfile(false)}
            >
                {showProfile && (
                    <div className="absolute left-14 bottom-0 w-64 rounded-xl border border-border bg-card/95 backdrop-blur-sm p-4 shadow-xl z-50 animate-in fade-in slide-in-from-left-2">
                        <div className="flex items-center gap-3 border-b border-border/50 pb-3 mb-3">
                            <div className="h-10 w-10 rounded-full bg-blue-500/10 flex items-center justify-center text-sm font-bold text-blue-500 border border-blue-500/20">
                                JS
                            </div>
                            <div>
                                <div className="font-semibold text-sm text-foreground">John Smith</div>
                                <div className="text-xs text-muted-foreground">Senior Security Analyst</div>
                            </div>
                        </div>
                        <div className="space-y-2">
                            <div className="flex justify-between text-xs">
                                <span className="text-muted-foreground">User ID</span>
                                <span className="font-mono text-foreground bg-muted/50 px-1.5 py-0.5 rounded">EMP-2026-8842</span>
                            </div>
                            <div className="flex justify-between text-xs">
                                <span className="text-muted-foreground">Role</span>
                                <span className="text-blue-500 bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/20">Admin</span>
                            </div>
                            <div className="pt-2 mt-2 border-t border-border/50">
                                <button className="w-full text-xs text-red-500 hover:text-red-400 flex items-center gap-2 transition-colors px-1 py-1 rounded hover:bg-red-500/10">
                                    <LogOut className="h-3 w-3" /> Sign Out
                                </button>
                            </div>
                        </div>
                    </div>
                )}
                <div className="h-8 w-8 rounded-full bg-blue-500/10 flex items-center justify-center text-xs font-bold text-blue-500 border border-blue-500/20 cursor-pointer hover:bg-blue-500/20 transition-colors ring-offset-background hover:ring-2 ring-blue-500/20">
                    JS
                </div>
            </div>
        </aside>
    );
};

const Layout: React.FC = () => {
    return (
        <div className="h-screen w-screen bg-background font-sans antialiased overflow-hidden flex">
            <Sidebar />
            <main className="flex-1 h-full overflow-hidden p-3 relative">
                <Outlet />
            </main>
        </div>
    );
};

export default Layout;
