/**
 * Cloudera Agent Studio View
 * Opens the Agent Studio workflow interface in a new window
 */

import { ExternalLink, Bot, Workflow, MessageSquare } from 'lucide-react';

const AgentStudioView = () => {
  const studioUrl = import.meta.env.VITE_AGENT_STUDIO_URL || "";

  const handleOpenStudio = () => {
    window.open(studioUrl, '_blank', 'noopener,noreferrer');
  };

  return (
    <div className="w-full min-h-[500px] bg-gray-800 rounded-lg p-8">
      <div className="max-w-3xl mx-auto text-center">
        {/* Header */}
        <div className="mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-blue-600/20 rounded-full mb-4">
            <Bot className="w-10 h-10 text-blue-400" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Cloudera Agent Studio</h2>
          <p className="text-gray-400">
            Multi-agent AI workflow for network operations analysis
          </p>
        </div>

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-gray-700/50 rounded-lg p-4">
            <Workflow className="w-8 h-8 text-green-400 mx-auto mb-2" />
            <h3 className="text-white font-medium mb-1">10 Specialized Agents</h3>
            <p className="text-gray-400 text-sm">RF, Power, Hardware, Weather, Geographic, and more</p>
          </div>
          <div className="bg-gray-700/50 rounded-lg p-4">
            <MessageSquare className="w-8 h-8 text-purple-400 mx-auto mb-2" />
            <h3 className="text-white font-medium mb-1">Natural Language</h3>
            <p className="text-gray-400 text-sm">Ask questions about network performance in plain English</p>
          </div>
          <div className="bg-gray-700/50 rounded-lg p-4">
            <Bot className="w-8 h-8 text-orange-400 mx-auto mb-2" />
            <h3 className="text-white font-medium mb-1">NOC Manager</h3>
            <p className="text-gray-400 text-sm">Coordinates analysis across all specialist agents</p>
          </div>
        </div>

        {/* Example Queries */}
        <div className="bg-gray-700/30 rounded-lg p-4 mb-8 text-left">
          <h3 className="text-white font-medium mb-3">Example Queries:</h3>
          <ul className="text-gray-400 text-sm space-y-2">
            <li>• "Analyze the backhaul issues affecting latency in our European nodes"</li>
            <li>• "Retrieve KPI data for Nokia nodes and identify any anomalies"</li>
            <li>• "Which nodes are likely to fail in the next 2 hours?"</li>
            <li>• "How is weather affecting node performance in the UK?"</li>
            <li>• "Compare call drop rates between manufacturers"</li>
          </ul>
        </div>

        {/* Open Button */}
        <button
          onClick={handleOpenStudio}
          className="inline-flex items-center gap-3 px-8 py-4 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors text-lg"
        >
          <span>Open Agent Studio</span>
          <ExternalLink className="w-5 h-5" />
        </button>

        <p className="text-gray-500 text-sm mt-4">
          Opens in a new browser tab
        </p>
      </div>
    </div>
  );
};

export default AgentStudioView;
