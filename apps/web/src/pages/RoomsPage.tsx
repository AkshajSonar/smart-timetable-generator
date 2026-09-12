import { useEffect, useState } from 'react';
import { Search, Plus, Monitor, BookOpen, Presentation, Users2, MoreVertical, Loader2 } from 'lucide-react';
import { api, type Room } from '../api/client';
import { useTenant } from '../lib/TenantContext';

function getIconForType(type: string) {
  const t = type.toLowerCase();
  if (t.includes('lab')) return { icon: Monitor, color: 'text-emerald-600', bg: 'bg-emerald-50' };
  if (t.includes('seminar')) return { icon: Presentation, color: 'text-purple-600', bg: 'bg-purple-50' };
  if (t.includes('auditorium')) return { icon: Users2, color: 'text-rose-600', bg: 'bg-rose-50' };
  return { icon: BookOpen, color: 'text-indigo-600', bg: 'bg-indigo-50' };
}

export function RoomsPage() {
  const { tenantId } = useTenant();
  const [activeTab, setActiveTab] = useState('All');
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    async function loadData() {
      if (!tenantId) return;
      try {
        const res = await api.rooms.list(tenantId);
        setRooms(res.items);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [tenantId]);

  const filteredRooms = rooms.filter(r => {
    if (activeTab !== 'All') {
      const typeStr = r.type.toLowerCase();
      const tabStr = activeTab.toLowerCase();
      // Simple mapping since the UI tabs don't perfectly match types
      if (tabStr === 'classrooms' && typeStr !== 'classroom') return false;
      if (tabStr === 'labs' && typeStr !== 'lab') return false;
      if (tabStr === 'seminar halls' && typeStr !== 'seminar hall') return false;
      if (tabStr === 'auditorium' && typeStr !== 'auditorium') return false;
    }
    if (search && !(r.name.toLowerCase().includes(search.toLowerCase()) || r.type.toLowerCase().includes(search.toLowerCase()))) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Rooms & Labs</h1>
          <p className="text-slate-500">Manage classrooms, labs, and other resources.</p>
        </div>
        <button className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors shadow-sm">
          <Plus className="w-4 h-4" />
          Add Room
        </button>
      </header>

      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between gap-4">
          <div className="relative w-72 shrink-0">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search rooms..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-white border border-slate-200 rounded-lg pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm placeholder:text-slate-400"
            />
          </div>
          <div className="flex gap-2 p-1 bg-white border border-slate-200 rounded-xl shadow-sm">
            {['All', 'Classrooms', 'Labs', 'Seminar Halls', 'Auditorium'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  activeTab === tab ? 'bg-slate-100 text-slate-900' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center min-h-[300px]">
            <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
          </div>
        ) : filteredRooms.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center shadow-sm">
            <p className="text-slate-500">No rooms found.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredRooms.map((room) => {
              const style = getIconForType(room.type);
              const Icon = style.icon;
              return (
                <div key={room.id} className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow group relative flex flex-col">
                  <button className="absolute top-4 right-4 p-1 text-slate-400 hover:text-slate-600 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                    <MoreVertical className="w-5 h-5" />
                  </button>
                  
                  <div className="flex items-start gap-4 mb-4">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${style.bg} ${style.color}`}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-900 text-lg leading-tight">{room.name}</h3>
                      <p className="text-slate-500 text-sm">{room.type.charAt(0).toUpperCase() + room.type.slice(1)}</p>
                    </div>
                  </div>
    
                  <div className="flex flex-wrap gap-2 mb-6">
                    {room.equipment_tags.map((eq, idx) => (
                      <span key={idx} className="px-2.5 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded-md">
                        {eq}
                      </span>
                    ))}
                    {room.equipment_tags.length === 0 && (
                      <span className="px-2.5 py-1 bg-slate-50 text-slate-400 text-xs font-medium rounded-md">No specific equipment</span>
                    )}
                  </div>
    
                  <div className="mt-auto pt-4 border-t border-slate-100">
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-slate-500">Capacity</span>
                      <span className="font-bold text-slate-900">{room.capacity} seats</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2 mb-3">
                      <div 
                        className={`h-2 rounded-full ${
                          room.capacity >= 100 ? 'bg-rose-500' :
                          room.capacity >= 50 ? 'bg-indigo-500' :
                          'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.min(100, (room.capacity / 150) * 100)}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-slate-400">Max 150</span>
                      {room.accessible ? (
                        <span className="text-emerald-600 font-medium">Accessible</span>
                      ) : (
                        <span className="text-slate-400">Standard</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
