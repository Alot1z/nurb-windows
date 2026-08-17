import { openUrl } from "@tauri-apps/plugin-opener";
import { AGENT_LABEL } from "./Chat";

type MissingAgent = {
  id: string;
  label: string;
  note: string;
  install: string | null;
};

/// The "need another agent?" help: the supported agents that are not on this
/// machine, each with its vendor's installer, and the road to asking for one
/// the app does not host yet.
function isWindows() {
  return /windows/i.test(navigator.userAgent);
}

export default function AgentsHelp({
  missing,
  onClose,
}: {
  missing: MissingAgent[];
  onClose: () => void;
}) {
  const shell = isWindows() ? "PowerShell" : "Terminal";
  const machine = isWindows() ? "this PC" : "your Mac";
  return (
    <div className="about" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="about-card agents-help">
        <button className="about-close" title="close" onClick={onClose}>
          ×
        </button>
        <div className="about-title">More agents</div>
        <div className="about-body">
          {missing.length > 0 ? (
            <>
              <p>
                Paste the line into {shell} to install the tool. Cursor and Grok
                then appear in the agent list when you come back; each card says
                what its subscription costs.
              </p>
              {missing.map((agent) => (
                <div className="agents-help-agent" key={agent.id}>
                  <p>
                    <b>{AGENT_LABEL[agent.id] ?? agent.label}</b> {agent.note}
                  </p>
                  {agent.install && <pre>{agent.install}</pre>}
                </div>
              ))}
            </>
          ) : (
            <p>Every agent nurb supports is already installed on {machine}.</p>
          )}
          <p>
            Using one that isn't here?{" "}
            <a
              href="https://github.com/Alot1z/nurb-windows/issues/new?template=feature_request.yml"
              onClick={(e) => {
                e.preventDefault();
                openUrl("https://github.com/Alot1z/nurb-windows/issues/new?template=feature_request.yml");
              }}
            >
              Ask for it on GitHub.
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
