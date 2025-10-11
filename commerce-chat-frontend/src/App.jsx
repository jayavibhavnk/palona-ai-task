import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/* ---------- Error Boundary so you never get a white screen ---------- */
class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, info) {
    console.error("App crashed:", error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6">
          <h1 className="text-lg font-semibold mb-2">Something went wrong</h1>
          <pre className="text-red-600 whitespace-pre-wrap text-sm bg-red-50 p-3 rounded">
            {String(this.state.error?.message || this.state.error)}
          </pre>
          <p className="text-sm text-gray-600 mt-2">
            Check the terminal and browser console for details. If you paste
            this message to me, I’ll fix it.
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}

/* ----------------------- Config & helpers ----------------------- */
const BACKEND_BASE =
  import.meta.env.VITE_API_BASE ||
  "https://macro-crane-474800-p9.uw.r.appspot.com";

const DEFAULT_SESSION = () =>
  localStorage.getItem("commerce_session_id") ||
  (() => {
    // Fallback if crypto.randomUUID() isn’t available
    const id =
      (crypto?.randomUUID && crypto.randomUUID()) ||
      "sess-" + Date.now() + "-" + Math.random().toString(16).slice(2);
    localStorage.setItem("commerce_session_id", id);
    return id;
  })();

async function api(path, payload) {
  const res = await fetch(`${BACKEND_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json();
}

function cx(...args) {
  return args.filter(Boolean).join(" ");
}

function formatPrice(p) {
  if (p == null || p === "") return "";
  if (typeof p === "number") return `$${p.toFixed(2)}`;
  const s = String(p);
  return s.startsWith("$") ? s : `$${s}`;
}

/* ----------------------- UI primitives ----------------------- */
const Button = ({ className = "", ...props }) => (
  <button
    className={cx(
      "px-4 py-2 rounded-2xl shadow-sm border border-gray-200",
      "bg-white hover:bg-gray-50 active:scale-[0.99] transition",
      className
    )}
    {...props}
  />
);

const Icon = ({ name, className = "w-5 h-5" }) => {
  const paths = {
    send: (
      <path
        d="M2.5 2.5l19 9-19 9 5-9-5-9zm5 9h9"
        stroke="currentColor"
        strokeWidth="1.5"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
    image: (
      <path
        d="M4 5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5zm4 4a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm12 10-6-6-4 4-3-3-5 5"
        stroke="currentColor"
        strokeWidth="1.5"
        fill="none"
        strokeLinecap="round"
      />
    ),
    cart: (
      <path
        d="M3 5h2l2.5 12.5a2 2 0 0 0 2 1.5h7a2 2 0 0 0 2-1.5L21 9H7"
        stroke="currentColor"
        strokeWidth="1.5"
        fill="none"
        strokeLinecap="round"
      />
    ),
    trash: (
      <path
        d="M3 6h18M8 6V4h8v2m-9 0v12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6"
        stroke="currentColor"
        strokeWidth="1.5"
        fill="none"
        strokeLinecap="round"
      />
    ),
    spinner: (
      <>
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
          fill="none"
        />
        <path
          className="opacity-75"
          d="M4 12a8 8 0 0 1 8-8"
          stroke="currentColor"
          strokeWidth="4"
          fill="none"
        />
      </>
    ),
  };
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden>
      {paths[name]}
    </svg>
  );
};

/* ----------------------- Product card ----------------------- */
function ProductCard({ p, onAdd }) {
  return (
    <div className="w-full md:max-w-[520px] rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      <div className="flex gap-4 p-3">
        <img
          src={p.image_url || "https://placehold.co/160x160?text=No+Image"}
          alt={p.product_name}
          className="w-24 h-24 object-cover rounded-xl border"
          loading="lazy"
        />
        <div className="flex-1 min-w-0">
          <h4
            className="font-semibold text-gray-900 truncate"
            title={p.product_name}
          >
            {p.product_name}
          </h4>
          {p.price && (
            <div className="text-sm text-emerald-700 font-medium mt-0.5">
              {formatPrice(p.price)}
            </div>
          )}
          {p.description && (
            <p className="text-sm text-gray-600 line-clamp-3 mt-1">
              {p.description}
            </p>
          )}
          <div className="flex items-center gap-2 mt-2">
            {p.url && (
              <a
                href={p.url}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-blue-600 hover:underline"
              >
                View
              </a>
            )}
            <Button className="ml-auto" onClick={onAdd}>
              Add to cart
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ----------------------- Bubbles (Markdown for assistant) ----------------------- */
function Bubble({ role, text }) {
  const isUser = role === "user";
  return (
    <div className={cx("w-full flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cx(
          "max-w-[85%] md:max-w-[70%] rounded-3xl px-4 py-3 leading-relaxed",
          isUser
            ? "bg-blue-600 text-white rounded-br-md"
            : "bg-white text-gray-900 border border-gray-200 rounded-bl-md shadow-sm"
        )}
      >
        {isUser ? (
          <div className="whitespace-pre-wrap break-words">{text}</div>
        ) : (
<div className="prose prose-sm max-w-none break-words">
  <ReactMarkdown remarkPlugins={[remarkGfm]}>
    {text}
  </ReactMarkdown>
</div>

        )}
      </div>
    </div>
  );
}

/* ----------------------- Main App ----------------------- */
function InnerApp() {
  const [sessionId, setSessionId] = useState(DEFAULT_SESSION());
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState(() => [
    {
      role: "assistant",
      text:
        "**Hey! I'm ShopAI.**\n\nAsk me for product ideas (e.g., _recommend running shoes under $100_), or **drag & drop** an image onto the bottom bar to find similar items. You can also manage a cart with commands like `add #2` or `view cart`.",
    },
  ]);
  const [cart, setCart] = useState([]);
  const [lastResults, setLastResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const listRef = useRef(null);

// only react when the number of messages changes (not while typing)
useEffect(() => {
  if (!listRef.current) return;
  const last = listRef.current.querySelector("[data-last]");
  last?.scrollIntoView({ behavior: "instant", block: "end" });
}, [messages.length]);


  const sendChat = async (query) => {
    setLoading(true);
    try {
      const userMsg = { role: "user", text: query };
      setMessages((m) => [...m, userMsg]);

      const data = await api("/chat", { session_id: sessionId, query });

      setLastResults(data.products || []);
      setCart(data.cart || []);

      const assistantMsg = {
        role: "assistant",
        text: data.answer,
        products: data.products,
      };
      setMessages((m) => [...m, assistantMsg]);
    } catch (e) {
      console.error(e);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `❌ ${e.message || "Something went wrong"}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const sendImage = async (imageInput, query = "Find similar products") => {
    if (!imageInput) return;
    setLoading(true);
    try {
      const userMsg = {
        role: "user",
        text:
          typeof imageInput === "string" && imageInput.startsWith("http")
            ? `🖼️ ${query}: ${imageInput}`
            : "🖼️ Uploaded image",
      };
      setMessages((m) => [...m, userMsg]);

      const payload =
        typeof imageInput === "string" && imageInput.startsWith("http")
          ? { session_id: sessionId, image_url: imageInput, query }
          : { session_id: sessionId, image_b64: imageInput, query };

      const data = await api("/image", payload);

      setLastResults(data.products || []);
      setCart(data.cart || []);

      const assistantMsg = {
        role: "assistant",
        text: data.answer,
        products: data.products,
      };
      setMessages((m) => [...m, assistantMsg]);
    } catch (e) {
      console.error(e);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `❌ ${e.message || "Something went wrong"}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const q = input.trim();
    if (!q) return;
    setInput("");
    sendChat(q);
  };

  const addToCart = async (idx) => {
    setLoading(true);
    try {
      const data = await api("/cart/add", {
        session_id: sessionId,
        item: `#${idx + 1}`,
      });
      setCart(data.cart || []);
      setLastResults(data.products || lastResults);
      setMessages((m) => [...m, { role: "assistant", text: data.answer }]);
    } catch (e) {
      console.error(e);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `❌ ${e.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const viewCart = async () => {
    setLoading(true);
    try {
      const data = await api("/cart/view", { session_id: sessionId });
      setCart(data.cart || []);
      setLastResults(data.products || lastResults);
      setMessages((m) => [...m, { role: "assistant", text: data.answer }]);
    } catch (e) {
      console.error(e);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `❌ ${e.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const removeFromCart = async (item) => {
    setLoading(true);
    try {
      const data = await api("/cart/remove", { session_id: sessionId, item });
      setCart(data.cart || []);
      setMessages((m) => [...m, { role: "assistant", text: data.answer }]);
    } catch (e) {
      console.error(e);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `❌ ${e.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const checkout = async () => {
    setLoading(true);
    try {
      const data = await api("/cart/checkout", { session_id: sessionId });
      setCart(data.cart || []);
      setMessages((m) => [...m, { role: "assistant", text: data.answer }]);
    } catch (e) {
      console.error(e);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `❌ ${e.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const resetSession = async () => {
    setLoading(true);
    try {
      const newId =
        (crypto?.randomUUID && crypto.randomUUID()) ||
        "sess-" + Date.now() + "-" + Math.random().toString(16).slice(2);
      localStorage.setItem("commerce_session_id", newId);
      setSessionId(newId);
      const res = await api("/session/reset", { session_id: newId });
      setMessages([{ role: "assistant", text: res.answer }]);
      setCart([]);
      setLastResults([]);
    } catch (e) {
      console.error(e);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `❌ ${e.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = () => sendImage(reader.result);
      reader.readAsDataURL(file);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white text-gray-900">
      {/* Header */}
      <header className="sticky top-0 z-10 backdrop-blur bg-white/70 border-b">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-3">
          <div className="w-9 h-9 rounded-2xl bg-blue-600 text-white grid place-items-center font-bold">
            S
          </div>
          <div className="flex-1">
            <div className="font-semibold">ShopAI</div>
            <div className="text-xs text-gray-500">Session: {sessionId.slice(0, 8)}…</div>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={viewCart} className="flex items-center gap-2">
              <Icon name="cart" /> Cart 
            </Button>
            <Button onClick={resetSession} className="text-red-600 border-red-200">
              New Session
            </Button>
          </div>
        </div>
      </header>

      {/* Chat area */}
      <main
  className="max-w-5xl mx-auto px-4 pt-6 pb-[200px] scroll-smooth"
  ref={listRef}
  style={{ scrollBehavior: "auto" }}
>

        <div className="space-y-4">
          {messages.map((m, i) => (
            <div key={i} className="space-y-3">
              <Bubble role={m.role} text={m.text} />
              {m.products?.length ? (
                <div
                  className={cx(
                    "grid gap-3",
                    m.role === "assistant" ? "grid-cols-1 md:grid-cols-2" : "grid-cols-1"
                  )}
                >
                  {m.products.map((p, idx) => (
                    <ProductCard key={idx} p={p} onAdd={() => addToCart(idx)} />
                  ))}
                </div>
              ) : null}
            </div>
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-gray-500">
              <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24">
                <Icon name="spinner" />
              </svg>
              Thinking…
            </div>
          )}
        </div>
      </main>

      {/* Composer + Drag area */}
      <form
        onSubmit={handleSubmit}
        className="fixed bottom-0 inset-x-0 bg-white/90 backdrop-blur border-t"
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
      >
        <div className="max-w-5xl mx-auto px-4 py-3 flex flex-col gap-2">
<div
  className="flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed rounded-xl text-sm text-gray-600
             border-emerald-300 hover:border-emerald-500 hover:bg-emerald-50 transition cursor-pointer"
  style={{ minHeight: "56px", maxHeight: "64px" }}
>
  <Icon name="image" className="w-5 h-5 text-emerald-500 opacity-70" />
  <span>Drag & drop image to search</span>
</div>



          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask for ideas, e.g. ‘recommend wireless headphones under $150’"
              className="flex-1 px-4 py-3 rounded-3xl border focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
<Button
  type="submit"
  className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white border-emerald-500 shadow-sm hover:shadow-md transition"
>
  <Icon name="send" className="w-5 h-5" />
  Send
</Button>

          </div>
          <div className="text-xs text-gray-500">
            Tips: Say <span className="font-medium">“add #2”</span>,{" "}
            <span className="font-medium">“view cart”</span>,{" "}
            <span className="font-medium">“remove #1”</span>, or{" "}
            <span className="font-medium">“checkout”</span>.
          </div>
        </div>
      </form>

      {cart.length > 0 && (
        <div className="fixed right-4 bottom-32 w-[360px] max-h-[60vh] overflow-auto bg-white border border-gray-200 rounded-2xl shadow-xl">
          <div className="px-4 py-3 flex items-center justify-between border-b">
            <div className="font-semibold">Your Cart</div>
            <Button
              onClick={checkout}
              className="bg-emerald-600 text-white border-emerald-600 hover:bg-emerald-700"
            >
              Checkout
            </Button>
          </div>
          <div className="p-3 space-y-3">
            {cart.map((c, i) => (
              <div key={i} className="flex gap-3 items-center">
                <img
                  src={c.image_url || "https://placehold.co/64x64"}
                  alt="thumb"
                  className="w-12 h-12 rounded-lg border object-cover"
                />
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium truncate" title={c.product_name}>
                    {c.product_name}
                  </div>
                  <div className="text-xs text-gray-500 truncate">{formatPrice(c.price)}</div>
                </div>
                <Button onClick={() => removeFromCart(`#${i + 1}`)} className="text-red-600 border-red-200">
                  <Icon name="trash" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      <footer className="fixed left-2 bottom-2 text-[10px] text-gray-400">
        API: {BACKEND_BASE}
      </footer>
    </div>
  );
}

/* Wrap with error boundary so you never get a blank screen */
export default function App() {
  return (
    <AppErrorBoundary>
      <InnerApp />
    </AppErrorBoundary>
  );
}
