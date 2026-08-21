import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open as pickFolder } from "@tauri-apps/plugin-dialog";
import { playChime, setSoundEnabled, soundEnabled } from "./chime";
import type { ExtensionStatus } from "./ExtensionsModal";

type Props = {
  folder: string;
  customized: boolean;
  onChange: (folder: string) => void | Promise<void>;
  onReset: () => void | Promise<void>;
  extensions: ExtensionStatus[];
  onExtensionsChanged: () => void;
  onClose: () => void;
};

export default function Settings({
  folder,
  customized,
  onChange,
  onReset,
  extensions,
  onExtensionsChanged,
  onClose,
}: Props) {
  const [sound, setSound] = useState(soundEnabled);

  const toggleSound = (on: boolean) => {
    setSoundEnabled(on);
    setSound(on);
    // Turning it on plays the chime once, so the choice is audible in place.
    if (on) playChime();
  };

  const toggleExtension = (id: string, enabled: boolean) => {
    invoke("set_extension_enabled", { id, enabled })
      .then(onExtensionsChanged)
      .catch(() => {});
  };

  const changeFolder = async () => {
    // Before the backend resolves the default, the folder shown is the
    // literal "~/Documents/nurb" placeholder, which is not a path.
    const picked = await pickFolder({
      directory: true,
      defaultPath: folder.startsWith("~") ? undefined : folder,
      title: "Choose where new nurb projects are created",
    });
    if (typeof picked === "string") await onChange(picked);
  };

  // Non-dev-only extensions get a toggle in settings; dev-only ones stay
  // behind the "developer extensions" modal where they belong.
  const visibleExts = extensions.filter((e) => !e.devOnly);

  return (
    <div className="about" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div
        className="about-card settings"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
      >
        <button className="about-close" title="close" onClick={onClose}>
          ×
        </button>
        <div className="about-title" id="settings-title">
          Settings
        </div>
        <div className="about-body">
          <h3>Projects folder</h3>
          <p>New projects are created here. Changing it never moves existing files.</p>
          <div className="settings-folder" title={folder}>
            {folder}
          </div>
          <div className="settings-actions">
            <button className="settings-action" onClick={changeFolder}>
              Change folder
            </button>
            {customized && (
              <button className="settings-action secondary" onClick={onReset}>
                Use default
              </button>
            )}
          </div>
          <h3>Sound</h3>
          <label className="settings-toggle">
            <input
              type="checkbox"
              checked={sound}
              onChange={(e) => toggleSound(e.target.checked)}
            />
            Play a chime when the agent finishes a long task
          </label>
          {visibleExts.length > 0 && (
            <>
              <h3>Extensions</h3>
              {visibleExts.map((ext) => (
                <label className="settings-toggle" key={ext.id}>
                  <input
                    type="checkbox"
                    checked={ext.enabled}
                    onChange={(e) => toggleExtension(ext.id, e.target.checked)}
                  />
                  {ext.label}
                  {!ext.installed && (
                    <span className="tag tag-off" style={{ marginLeft: 6 }}>
                      not installed
                    </span>
                  )}
                </label>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
