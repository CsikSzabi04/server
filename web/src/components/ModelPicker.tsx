import { useState } from 'react';
import { useModels, type ModelOption } from '../lib/aiModels';
import { addCustomModel, removeCustomModel, setSelectedModel, type ByoProvider } from '../lib/modelStore';

// Model dropdown for the composer: lists Auto/hosted, the local Ollama models
// (disabled when the PC is offline), and the user's own BYO providers — plus an
// inline form to add & save an API key (kept on-device only).
export default function ModelPicker() {
  const { options, prefs } = useModels();
  const [open, setOpen] = useState(false);
  const [adding, setAdding] = useState(false);

  const [provider, setProvider] = useState<ByoProvider>('openai');
  const [label, setLabel] = useState('');
  const [model, setModel] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');

  const current = options.find((o) => o.id === prefs.selectedId);

  const groups: Record<string, ModelOption[]> = {};
  for (const o of options) {
    if (!groups[o.group]) groups[o.group] = [];
    groups[o.group].push(o);
  }

  const save = () => {
    if (!apiKey.trim() || !model.trim()) return;
    addCustomModel({
      provider,
      label: label.trim() || model.trim(),
      model: model.trim(),
      apiKey: apiKey.trim(),
      baseUrl: provider === 'openai' ? baseUrl.trim() || undefined : undefined,
    });
    setAdding(false);
    setOpen(false);
    setLabel('');
    setModel('');
    setBaseUrl('');
    setApiKey('');
  };

  return (
    <div className="model-picker">
      <button className="model-trigger" onClick={() => setOpen((v) => !v)} aria-expanded={open} title="Choose model">
        <span className="model-spark">✦</span>
        <span className="model-name">{current?.label ?? 'Auto'}</span>
        <span className="model-caret">⌄</span>
      </button>

      {open && (
        <>
          <div className="model-backdrop" onClick={() => setOpen(false)} />
          <div className="model-menu">
            {Object.entries(groups).map(([g, list]) => (
              <div key={g} className="model-group">
                <div className="model-group-h">{g}</div>
                {list.map((o) => (
                  <button
                    key={o.id}
                    className={`model-item${o.id === prefs.selectedId ? ' active' : ''}${o.available ? '' : ' disabled'}`}
                    disabled={!o.available}
                    onClick={() => {
                      setSelectedModel(o.id);
                      setOpen(false);
                    }}
                  >
                    <span className="model-item-label">{o.label}</span>
                    <span className="model-item-detail">{o.detail}</span>
                    {o.custom && (
                      <span
                        className="model-del"
                        title="Remove"
                        onClick={(e) => {
                          e.stopPropagation();
                          removeCustomModel(o.custom!.id);
                        }}
                      >
                        ✕
                      </span>
                    )}
                  </button>
                ))}
              </div>
            ))}

            {!adding ? (
              <button className="model-add" onClick={() => setAdding(true)}>
                ＋ Add your API key
              </button>
            ) : (
              <div className="model-form">
                <div className="model-form-row">
                  <button className={`mf-tab${provider === 'openai' ? ' on' : ''}`} onClick={() => setProvider('openai')}>
                    OpenAI-compatible
                  </button>
                  <button className={`mf-tab${provider === 'gemini' ? ' on' : ''}`} onClick={() => setProvider('gemini')}>
                    Gemini
                  </button>
                </div>
                <input className="auth-input" placeholder="label (e.g. My GPT-4o)" value={label} onChange={(e) => setLabel(e.target.value)} />
                <input
                  className="auth-input"
                  placeholder={provider === 'gemini' ? 'model (e.g. gemini-2.0-flash)' : 'model (e.g. gpt-4o-mini)'}
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                />
                {provider === 'openai' && (
                  <input
                    className="auth-input"
                    placeholder="base URL — blank = OpenAI (Groq/OpenRouter ok)"
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                  />
                )}
                <input
                  className="auth-input"
                  type="password"
                  placeholder="API key (saved on this device only)"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
                <div className="model-form-row">
                  <button className="auth-submit" onClick={save}>
                    Save &amp; use
                  </button>
                  <button className="auth-switch" onClick={() => setAdding(false)}>
                    Cancel
                  </button>
                </div>
                <div className="model-form-note">
                  Stored only in this browser — your key is never sent to our server.
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
