import { memo } from 'react';
import { TrendingUp, TrendingDown, Minus, Package, Settings, Zap, MapPin } from 'lucide-react';
import { CommonIssueData } from '@/services/analyticsService';
import { IssueCategory } from '@/types';

interface CommonIssuesPanelProps {
  issues: CommonIssueData[];
}

const CommonIssuesPanel = memo(({ issues }: CommonIssuesPanelProps) => {

  const getCategoryIcon = (category: IssueCategory) => {
    switch (category) {
      case IssueCategory.EQUIPMENT:
        return Package;
      case IssueCategory.CONFIGURATION:
        return Settings;
      case IssueCategory.CAPACITY:
        return Zap;
      default:
        return Package;
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing':
        return TrendingUp;
      case 'decreasing':
        return TrendingDown;
      default:
        return Minus;
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'increasing':
        return 'text-red-500';
      case 'decreasing':
        return 'text-green-500';
      default:
        return 'text-gray-500';
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6 h-full flex flex-col">
      <h2 className="text-lg font-semibold text-white mb-4">
        Common Issues Analytics {issues.length > 0 && `(${issues.length})`}
      </h2>
      <div className="space-y-4 flex-1 overflow-y-auto">
        {issues.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            No common patterns detected yet
          </p>
        ) : (
          issues.map((issue, index) => {
            const Icon = getCategoryIcon(issue.category);
            const TrendIcon = getTrendIcon(issue.trend);
            const trendColor = getTrendColor(issue.trend);
            return (
              <div key={index} className="border border-gray-700 rounded-lg p-4 bg-gray-750">
                <div className="flex items-start gap-3">
                  <Icon className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs px-2 py-0.5 rounded bg-blue-600 text-white">
                        {issue.category}
                      </span>
                      <div className="flex items-center gap-1">
                        <TrendIcon className={`w-3 h-3 ${trendColor}`} />
                        <span className={`text-xs ${trendColor}`}>{issue.trend}</span>
                      </div>
                    </div>
                    <p className="text-sm font-medium text-white mb-2">{issue.description}</p>
                    <div className="flex items-center gap-4 text-xs text-gray-400 mb-2">
                      <span>{issue.occurrences} occurrences</span>
                      <span>{issue.affectedNodes} nodes affected</span>
                    </div>

                    {/* Affected Cities */}
                    {issue.affectedCities.length > 0 && (
                      <div className="mb-2 flex items-start gap-1">
                        <MapPin className="w-3 h-3 text-orange-400 flex-shrink-0 mt-0.5" />
                        <div>
                          <span className="text-xs font-medium text-orange-400">Urban areas: </span>
                          <span className="text-xs text-gray-300">
                            {issue.affectedCities.join('; ')}
                          </span>
                        </div>
                      </div>
                    )}

                    <div className="mt-2">
                      <p className="text-xs font-medium text-gray-300 mb-1">Common Factors:</p>
                      <ul className="text-xs text-gray-400 space-y-0.5">
                        {issue.commonFactors.map((factor, idx) => (
                          <li key={idx}>• {factor}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
});

CommonIssuesPanel.displayName = 'CommonIssuesPanel';

export default CommonIssuesPanel;
