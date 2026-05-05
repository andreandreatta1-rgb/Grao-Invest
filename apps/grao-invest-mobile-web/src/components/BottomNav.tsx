type BottomNavProps<T extends string> = {
  items: { id: T; label: string; icon: string }[];
  activeItem: T;
  onChange: (item: T) => void;
};

export function BottomNav<T extends string>({ items, activeItem, onChange }: BottomNavProps<T>) {
  return (
    <div className="flex gap-1 border-t border-white/7 bg-gradient-to-t from-grao-bg2 to-transparent px-4 pb-7 pt-3">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => onChange(item.id)}
          className={`flex flex-1 flex-col items-center gap-1 rounded-[14px] p-2 transition-all duration-200 ${
            activeItem === item.id ? "bg-grao-green/10" : "hover:bg-white/[0.04]"
          }`}
        >
          <span className="text-xl" aria-hidden="true">{item.icon}</span>
          <span className={`text-[10px] font-semibold ${activeItem === item.id ? "text-grao-green" : "text-grao-text3"}`}>
            {item.label}
          </span>
        </button>
      ))}
    </div>
  );
}
