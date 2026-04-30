const wsUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000')
    .replace(/\/$/, '')
    .replace(/^http/, 'ws') + '/ws';

class ArceuxWebSocket {
    private ws: WebSocket | null = null;
    private url: string;
    private reconnectDelay: number = 2000;
    private maxReconnectDelay: number = 30000;
    private reconnectAttempts: number = 0;
    private shouldReconnect: boolean = true;
    private listeners: Map<string, Set<(data: unknown) => void>> = new Map();
    private pingInterval: ReturnType<typeof setInterval> | null = null;
    private _connected: boolean = false;
    private _conversationHistory: Array<{ role: string; content: string }> = [];

    getConversationHistory(): Array<{ role: string; content: string }> {
        return this._conversationHistory;
    }

    addToConversationHistory(role: string, content: string): void {
        this._conversationHistory.push({ role, content });
        if (this._conversationHistory.length > 20) {
            this._conversationHistory = this._conversationHistory.slice(-20);
        }
    }

    clearConversationHistory(): void {
        this._conversationHistory = [];
    }

    constructor(url: string) {
        this.url = url;
    }

    get connected(): boolean {
        return this._connected;
    }

    connect(): void {
        if (
            this.ws &&
            (this.ws.readyState === WebSocket.OPEN ||
                this.ws.readyState === WebSocket.CONNECTING)
        ) {
            return;
        }

        this.shouldReconnect = true;

        try {
            this.ws = new WebSocket(this.url);
        } catch {
            this.scheduleReconnect();
            return;
        }

        this.ws.onopen = () => {
            this._connected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 2000;
            this.startPing();
            this._emit('__connected', null);
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data?.type) {
                    this._emit(data.type, data);
                }
            } catch {
                // ignore malformed frames
            }
        };

        this.ws.onclose = () => {
            this._connected = false;
            this.stopPing();
            this._emit('__disconnected', null);
            if (this.shouldReconnect) {
                this.scheduleReconnect();
            }
        };

        this.ws.onerror = () => {
            // onerror always precedes onclose — let onclose handle reconnect
        };
    }

    disconnect(): void {
        this.shouldReconnect = false;
        this.stopPing();
        this.ws?.close();
        this.ws = null;
        this._connected = false;
    }

    /** Register a callback for a message type. Returns an unsubscribe function. */
    on<T = unknown>(eventType: string, callback: (data: T) => void): () => void {
        if (!this.listeners.has(eventType)) {
            this.listeners.set(eventType, new Set());
        }
        const cb = callback as (data: unknown) => void;
        this.listeners.get(eventType)!.add(cb);
        return () => {
            this.listeners.get(eventType)?.delete(cb);
        };
    }

    private _emit(type: string, data: unknown): void {
        this.listeners.get(type)?.forEach((cb) => {
            try {
                cb(data);
            } catch {
                // isolate listener errors from each other
            }
        });
    }

    private startPing(): void {
        this.stopPing();
        this.pingInterval = setInterval(() => {
            if (this.ws?.readyState === WebSocket.OPEN) {
                try {
                    this.ws.send('ping');
                } catch {
                    // ignore
                }
            }
        }, 25000);
    }

    private stopPing(): void {
        if (this.pingInterval !== null) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    private scheduleReconnect(): void {
        const delay = this.reconnectDelay;
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
        this.reconnectAttempts++;
        setTimeout(() => {
            if (this.shouldReconnect) {
                this.connect();
            }
        }, delay);
    }
}

export const arceuxWS = new ArceuxWebSocket(wsUrl);
