import React from 'react';
import { SHAPDriver } from '../types';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface RiskDriverBarProps {
  drivers: SHAPDriver[];
  maxShap?: number;
}

export const RiskDriverBar: React.FC<RiskDriverBarProps> = ({ drivers, maxShap }) => {
  if (!drivers || drivers.length === 0) {
    return <p className="text-xs text-slate-500 italic">No SHAP driver data available.</p>;
  }

  const highestAbs = maxShap || Math.max(...drivers.map((d) => Math.abs(d.shap_value)), 0.01);

  return (
    <div className="space-y-3">
      {drivers.map((driver, idx) => {
        const absVal = Math.abs(driver.shap_value);
        const widthPct = Math.min(100, Math.max(8, (absVal / highestAbs) * 100));
        const isRiskIncreasing = driver.shap_value > 0 || driver.direction.includes('Increases');

        return (
          <div key={idx} className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <div className="flex items-center justify-between gap-2 text-xs mb-1.5">
              <div className="flex items-center gap-1.5 font-medium text-[#12213A] truncate">
                {isRiskIncreasing ? (
                  <TrendingUp className="w-3.5 h-3.5 text-red-600 shrink-0" />
                ) : (
                  <TrendingDown className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                )}
                <span className="truncate">{driver.plain_language_driver}</span>
              </div>
              <span className="font-mono font-bold tabular-nums shrink-0 text-slate-700">
                {driver.shap_value > 0 ? `+${driver.shap_value.toFixed(3)}` : driver.shap_value.toFixed(3)}
              </span>
            </div>

            {/* Horizontal Impact Bar */}
            <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ease-out ${
                  isRiskIncreasing ? 'bg-red-700' : 'bg-slate-500'
                }`}
                style={{ width: `${widthPct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};
