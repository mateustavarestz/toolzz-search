interface SkeletonProps {
    className?: string;
    style?: React.CSSProperties;
}

export function Skeleton({ className = '', style }: SkeletonProps) {
    return (
        <div
            className={`skeleton ${className}`}
            style={style}
        />
    );
}

export function SkeletonCard() {
    return (
        <div className="card space-y-3">
            <Skeleton style={{ height: '24px', width: '33%' }} />
            <Skeleton style={{ height: '16px', width: '100%' }} />
            <Skeleton style={{ height: '16px', width: '83%' }} />
            <div className="grid grid-cols-3 gap-4" style={{ paddingTop: '16px' }}>
                <Skeleton style={{ height: '80px', borderRadius: 'var(--radius-md)' }} />
                <Skeleton style={{ height: '80px', borderRadius: 'var(--radius-md)' }} />
                <Skeleton style={{ height: '80px', borderRadius: 'var(--radius-md)' }} />
            </div>
        </div>
    );
}
