import React from 'react';
import { useAuth } from '../context/AuthContext';
import { ShieldAlert } from 'lucide-react';

interface RoleGuardProps {
  allowedRoles: Array<'ADMIN' | 'CLINICIAN' | 'ANALYST'>;
  children: React.ReactNode;
}

export const RoleGuard: React.FC<RoleGuardProps> = ({ allowedRoles, children }) => {
  const { user } = useAuth();

  if (!user || !allowedRoles.includes(user.role)) {
    return (
      <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-xs max-w-lg mx-auto my-12 text-center space-y-3">
        <ShieldAlert className="w-10 h-10 text-amber-500 mx-auto" />
        <h2 className="text-base font-bold font-display text-[#12213A]">Restricted Role Access</h2>
        <p className="text-xs text-slate-500">
          Your active account role (<span className="font-mono font-bold text-slate-700">{user?.role || 'Guest'}</span>) does not have permission to view this view. Required role: <span className="font-mono font-bold text-slate-700">{allowedRoles.join(' or ')}</span>.
        </p>
      </div>
    );
  }

  return <>{children}</>;
};
