type TabBarProps<T extends string> = {
  tabs: { id: T; label: string }[];
  activeTab: T;
  onChange: (tab: T) => void;
};

export function TabBar<T extends string>({ tabs, activeTab, onChange }: TabBarProps<T>) {
  return (
    <div className="mx-6 mb-5 flex gap-1 rounded-2xl bg-grao-card p-1">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={`flex-1 rounded-xl px-2.5 py-2.5 text-center text-[13px] font-semibold transition-all duration-200 ${
            activeTab === tab.id
              ? "bg-gradient-to-br from-[#1a3a6a] to-[#1f4580] text-white shadow-[0_4px_12px_rgba(79,142,247,0.25)]"
              : "text-grao-text2 hover:bg-white/[0.05] hover:text-white"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
