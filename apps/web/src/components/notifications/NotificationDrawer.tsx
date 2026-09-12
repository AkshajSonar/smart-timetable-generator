import { useState, useEffect } from 'react';
import { Bell, Check, Settings, X, Mail, Smartphone, MessageSquare } from 'lucide-react';
import { useTenant } from '../../lib/TenantContext';
import { api } from '../../api/client';

export function NotificationDrawer() {
  const { tenantId } = useTenant();
  const [isOpen, setIsOpen] = useState(false);
  const [showPrefs, setShowPrefs] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [prefs, setPrefs] = useState({ email: true, push: true, sms: false });
  const [loading, setLoading] = useState(false);

  const fetchNotifications = async () => {
    if (!tenantId) return;
    try {
      const res = await api.notifications.list(tenantId);
      setNotifications(res.items || []);
      const prefRes = await api.notifications.getPreferences(tenantId);
      setPrefs(prefRes);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, [tenantId]);

  const markAsRead = async (id: string) => {
    if (!tenantId) return;
    try {
      await api.notifications.markRead(tenantId, id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, status: 'read' } : n));
    } catch (err) {
      console.error(err);
    }
  };

  const handleSavePrefs = async (newPrefs: typeof prefs) => {
    if (!tenantId) return;
    setPrefs(newPrefs);
    try {
      await api.notifications.updatePreferences(tenantId, newPrefs);
    } catch (err) {
      console.error(err);
    }
  };

  const unreadCount = notifications.filter(n => n.status !== 'read').length;

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 text-slate-400 hover:text-slate-600 transition-colors relative"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 min-w-4 h-4 px-1 bg-rose-500 text-white font-bold text-[10px] rounded-full flex items-center justify-center border-2 border-white">
            {unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 md:w-96 bg-white border border-slate-200 rounded-2xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-indigo-600" />
              <h3 className="font-bold text-slate-900 text-sm">Notifications</h3>
              {unreadCount > 0 && (
                <span className="bg-indigo-100 text-indigo-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                  {unreadCount} new
                </span>
              )}
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={() => setShowPrefs(!showPrefs)}
                className={`p-1.5 rounded-lg text-xs font-medium flex items-center gap-1 transition-colors ${
                  showPrefs ? 'bg-indigo-100 text-indigo-700' : 'text-slate-500 hover:bg-slate-100'
                }`}
                title="Notification Preferences"
              >
                <Settings className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {showPrefs ? (
            <div className="p-4 space-y-4 bg-slate-50/30">
              <div className="font-bold text-xs uppercase tracking-wider text-slate-500">Channel Preferences (FR-11.1)</div>
              
              <div className="space-y-2">
                {[
                  { key: 'email', label: 'Email Notifications', desc: 'Receive schedule publish & sub alerts via email', icon: Mail },
                  { key: 'push', label: 'In-App Push Alerts', desc: 'Real-time browser popups on schedule updates', icon: Smartphone },
                  { key: 'sms', label: 'SMS Notifications', desc: 'Urgent substitution requests via SMS', icon: MessageSquare },
                ].map(channel => (
                  <label
                    key={channel.key}
                    className="flex items-start justify-between p-3 rounded-xl border border-slate-200 bg-white cursor-pointer hover:bg-slate-50 transition-colors"
                  >
                    <div className="flex items-center gap-2.5">
                      <channel.icon className="w-4 h-4 text-slate-500 mt-0.5" />
                      <div>
                        <div className="text-xs font-bold text-slate-800">{channel.label}</div>
                        <div className="text-[10px] text-slate-400">{channel.desc}</div>
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={(prefs as any)[channel.key]}
                      onChange={(e) => handleSavePrefs({ ...prefs, [channel.key]: e.target.checked })}
                      className="mt-1 text-indigo-600 rounded focus:ring-indigo-500"
                    />
                  </label>
                ))}
              </div>

              <button
                onClick={() => setShowPrefs(false)}
                className="w-full bg-slate-900 text-white text-xs font-medium py-2 rounded-xl hover:bg-slate-800 transition-colors"
              >
                Done
              </button>
            </div>
          ) : (
            <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
              {notifications.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-xs">
                  No notifications yet.
                </div>
              ) : (
                notifications.map(n => (
                  <div
                    key={n.id}
                    onClick={() => markAsRead(n.id)}
                    className={`p-4 transition-colors cursor-pointer hover:bg-slate-50 ${
                      n.status !== 'read' ? 'bg-indigo-50/40' : 'bg-white'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-bold text-xs text-slate-900">{n.subject || 'Schedule Notification'}</span>
                      {n.status !== 'read' && (
                        <span className="w-2 h-2 rounded-full bg-indigo-600 shrink-0 mt-1"></span>
                      )}
                    </div>
                    <p className="text-xs text-slate-600 mt-1 leading-snug">{n.body}</p>
                    <div className="text-[10px] text-slate-400 mt-2 flex justify-between items-center">
                      <span>Channel: {n.channel}</span>
                      <span>{new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
