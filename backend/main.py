import os, base64, re, json, requests
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

USE_HARDCODED_CONNECT = True # because i have a vdb prepared for this 

from groq import Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("Set GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)


import weaviate
from weaviate.auth import AuthApiKey


try:
    from weaviate.classes.query import MetadataQuery  # v4
except Exception:
    MetadataQuery = None  # graceful fallback

def connect_weaviate():
    if USE_HARDCODED_CONNECT:
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url="xbgyazubtqg88blsthsv8w.c0.us-west3.gcp.weaviate.cloud",
            auth_credentials=AuthApiKey("YOUR_WCS_API_KEY"),
            headers={"X-Cohere-Api-Key": "YOUR_COHERE_API_KEY"}
        )
        return client

    # for env
    WEAVIATE_URL = os.getenv("WEAVIATE_URL")  # e.g. https://<cluster>.weaviate.network
    WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")
    WEAVIATE_LOCAL = os.getenv("WEAVIATE_LOCAL", "").lower() == "true"

    if WEAVIATE_LOCAL:
        return weaviate.connect_to_local()

    if not WEAVIATE_URL:
        raise RuntimeError("Set WEAVIATE_URL or WEAVIATE_LOCAL=true")

    headers = {"X-Cohere-Api-Key": COHERE_API_KEY} if COHERE_API_KEY else None
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=WEAVIATE_URL,
        auth_credentials=AuthApiKey(WEAVIATE_API_KEY) if WEAVIATE_API_KEY else None,
        headers=headers,
    )
    return client

client = connect_weaviate()
# expect your "Product" collection to already exist (as you created/imported it in your notebook)
coll = client.collections.get("Product")

# max memory
MEMORY_TURNS = 12

class SessionState(BaseModel):
    history: List[Dict[str, str]] = []
    last_results: List[Dict[str, Any]] = []
    cart: List[Dict[str, Any]] = []

SESSIONS: Dict[str, SessionState] = {}

def state_for(session_id: str) -> SessionState:
    if session_id not in SESSIONS:
        SESSIONS[session_id] = SessionState()
    return SESSIONS[session_id]

def trim_history(st: SessionState):
    while len(st.history) > MEMORY_TURNS:
        st.history.pop(0)


# base classes for chat
class ChatReq(BaseModel):
    session_id: str
    query: str

class ImageReq(BaseModel):
    session_id: str
    image_url: Optional[str] = None
    image_b64: Optional[str] = None
    query: Optional[str] = "Find similar products"

class CartAddReq(BaseModel):
    session_id: str
    item: Optional[str] = None  # "#2" or product name
    product: Optional[Dict[str, Any]] = None  # direct product payload

class CartRemoveReq(BaseModel):
    session_id: str
    item: str  # "#1" or name substring

class SessionReq(BaseModel):
    session_id: str

class ChatRes(BaseModel):
    answer: str
    products: List[Dict[str, Any]] = []
    cart: List[Dict[str, Any]] = []


# retrieval
def text_search(q: str, k: int = 5) -> List[Dict[str, Any]]:
    kwargs = dict(
        query=q,
        target_vector="mm_vec",
        limit=k,
        return_properties=["product_name","description","price","url","image_url", "review_count", "rating_overall", "reviews_json"],
    )
    if MetadataQuery is not None:
        kwargs["return_metadata"] = MetadataQuery(distance=True)

    res = coll.query.near_text(**kwargs)
    out=[]
    for o in (res.objects or []):
        p=o.properties
        out.append({
            "product_name": p.get("product_name",""),
            "description":  p.get("description",""),
            "price":        p.get("price",""),
            "url":          p.get("url",""),
            "image_url":    p.get("image_url",""),
            "review_count": p.get("review_count", ""),
            "rating_overall": p.get("rating_overall", ""),
            "reviews_json": p.get("reviews_json")
        })
    return out

def url_to_b64(url: str) -> str:
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return base64.b64encode(r.content).decode("utf-8")

def image_search(url: str, k: int = 5) -> List[Dict[str, Any]]:
    b64 = url_to_b64(url)
    kwargs = dict(
        near_image=b64,
        target_vector="mm_vec",
        limit=k,
        return_properties=["product_name","description","price","url","image_url", "review_count", "rating_overall", "reviews_json"],
    )
    if MetadataQuery is not None:
        kwargs["return_metadata"] = MetadataQuery(distance=True)

    res = coll.query.near_image(**kwargs)
    out=[]
    for o in (res.objects or []):
        p=o.properties
        out.append({
            "product_name": p.get("product_name",""),
            "description":  p.get("description",""),
            "price":        p.get("price",""),
            "url":          p.get("url",""),
            "image_url":    p.get("image_url",""),
            "review_count": p.get("review_count", ""),
            "rating_overall": p.get("rating_overall", ""),
            "reviews_json": p.get("reviews_json")
        })
    return out

def format_ctx(items: List[Dict[str, Any]], max_reviews_chars: int = 2000) -> str:
    if not items:
        return "(no product data retrieved)"
    lines = []
    for i, p in enumerate(items, 1):
        name = p.get("product_name", "")
        price = p.get("price", "")
        desc  = p.get("description", "")
        url   = p.get("url", "")
        rating = p.get("rating_overall", "")
        rcnt   = p.get("review_count", "")
        rjson  = p.get("reviews_json") or ""

        # Truncate oversized review payloads to protect token budget
        if isinstance(rjson, str) and len(rjson) > max_reviews_chars:
            rjson = rjson[:max_reviews_chars] + "...(truncated)"

        lines.append(
            f"{i}. {name} {price}\n"
            f"   Rating: {rating} ({rcnt})\n"
            f"   {desc}\n"
            f"   {url}\n"
            f"   reviews_json (parse this JSON array yourself):\n"
            f"   ```json\n{rjson}\n```"
        )
    return "\n\n".join(lines)



# groq inference
def llm_answer(context: str, user_query: str, use_history: Optional[List[Dict[str,str]]] = None) -> str:
    system = (
        "You are Ruf AI, an e-shopping assistant.\n you will explain about the product if required"
        "- Recommend strictly from the provided product data (do NOT invent items).\n"
        "- If user mentions #2, it refers to the latest results list.\n"
        "- Keep responses short; list top 3 unless asked otherwise. If uncertain, ask clarifying questions."
        "- You are a commerce focused agent, if you are asked any questions outside of this, you will let the user know what your purpose is."
    )
    messages = [{"role":"system","content":f"{system}\n\nProduct data:\n{context}"}]
    if use_history:
        messages += use_history
    messages.append({"role":"user","content":user_query})

    resp = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        temperature=0.4,
        max_completion_tokens=2048,
    )
    return resp.choices[0].message.content.strip()


# methods for cart
def add_idx(st: SessionState, idx: int) -> str:
    if not st.last_results:
        return "There are no recent results. Run a search, then use `add #2`."
    if idx < 1 or idx > len(st.last_results):
        return f"Pick a number between 1 and {len(st.last_results)}."
    item = st.last_results[idx-1]
    st.cart.append(item)
    return f"Added **{item['product_name']}** to your cart."

def add_name(st: SessionState, name: str) -> str:
    q = name.lower().strip()
    if st.last_results:
        for r in st.last_results:
            if q == r["product_name"].lower() or q in r["product_name"].lower():
                st.cart.append(r)
                return f"Added **{r['product_name']}** to your cart."
    hits = text_search(name, k=1)
    if hits:
        st.cart.append(hits[0])
        return f"Added **{hits[0]['product_name']}** to your cart."
    return "I couldn’t find that product. Try `add <exact product name>` or `add #2`."

def view_cart(st: SessionState) -> str:
    if not st.cart: return "🛒 Your cart is empty."
    lines=[]
    for i,r in enumerate(st.cart,1):
        lines.append(f"{i}. {r['product_name']} ({r.get('price','')}) {r.get('url','')}")
    return "🛒 Your cart:\n" + "\n".join(lines)

def remove_cart(st: SessionState, arg: str) -> str:
    if not st.cart: return "Your cart is empty."
    m = re.search(r"\d+", arg)
    if m:
        idx = int(m.group())
        if 1 <= idx <= len(st.cart):
            item = st.cart.pop(idx-1)
            return f"Removed **{item['product_name']}** from your cart."
    q = arg.lower().strip()
    for i,r in enumerate(st.cart):
        if q in r["product_name"].lower():
            item = st.cart.pop(i)
            return f"Removed **{item['product_name']}** from your cart."
    return "Didn’t find that item. Use an index like `remove #1` or a clear name."

def checkout(st: SessionState) -> str:
    if not st.cart: return "Your cart is empty."
    summary = "\n".join([f"- {r['product_name']} ({r.get('price','')})" for r in st.cart])
    n = len(st.cart)
    st.cart.clear()
    return f"✅ Checkout complete!\nItems:\n{summary}\nTotal items: {n}\n(Payment mocked.)"

def dataurl_to_b64(data_url: str) -> str:
    # expects 'data:image/png;base64,AAAA...'
    prefix = 'base64,'
    i = data_url.find(prefix)
    if i == -1:
        raise HTTPException(400, "Invalid data URL")
    return data_url[i+len(prefix):]

# API
app = FastAPI(title="Commerce Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def awake():
    return {"server": "Active"}

@app.get("/health")
def health():
    try:
        total = coll.aggregate.over_all(total_count=True).total_count
        return {"ok": True, "weaviate_version": weaviate.__version__, "count": total}
    except Exception as e:
        raise HTTPException(500, str(e))

def should_rag(user_query: str, recent_history: List[Dict[str, str]]) -> bool:
    sys = (
        "Decide if we should run product retrieval (RAG) for the next user turn.\n"
        "Respond ONLY with strict JSON like {\"rag\": true} or {\"rag\": false}.\n"
        "Heuristics (use your judgment, not keywords):\n"
        "- RAG = TRUE when the user asks to discover/find/compare products, wants reviews/specs/prices/alternatives, YES WHEN THE USER WANTS TO KNOW MORE ABOUT THE PRODUCT\n"
        "- RAG = FALSE when it's smalltalk, cart-only ops (add/remove/checkout/view), or a follow-up that does not require new items.\n"
        "- If uncertain, wait for the conversation to flow, if its the same item as previously discussed, then a new RAG pull is not required."
    )

    msgs = [{"role":"system","content":sys}]
    # keep it tiny to avoid drift
    for m in recent_history:
        msgs.append(m)
    msgs.append({"role":"user","content":f"User: {user_query}\nReturn JSON now."})

    try:
        resp = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=msgs,
            temperature=0.0,
            max_completion_tokens=100,
        )
        content = (resp.choices[0].message.content or "").strip()
        # extremely defensive JSON parse
        m = re.search(r'\{\s*"rag"\s*:\s*(true|false)\s*\}', content, flags=re.I)
        if not m:
            return True  # default to RAG when unclear
        return m.group(1).lower() == "true"
    except Exception:
        # On any classifier failure, default to TRUE (safer for shopping)
        return True

@app.post("/chat", response_model=ChatRes)
@app.post("/chat", response_model=ChatRes)
def chat(req: ChatReq):
    st = state_for(req.session_id)
    q = req.query.strip()

    do_rag = should_rag(q, st.history)

    products: List[Dict[str, Any]] = []
    if do_rag:
        products = text_search(q, k=5)
        if not products:
            q2 = re.sub(r"[^a-zA-Z0-9\s]", " ", q)
            q2 = re.sub(r"\s+", " ", q2).strip()
            if q2 and q2 != q:
                products = text_search(q2, k=5)
        if products:
            st.last_results = products[:]
    else:
        # ✅ critical: keep using previous results when the user is asking follow-ups (like “show me reviews”)
        products = st.last_results[:] if st.last_results else []

    context = format_ctx(products)  # (this will be updated in the next section)
    ans = llm_answer(context, q, use_history=st.history[-(MEMORY_TURNS-2):])

    st.history.append({"role":"user","content":q})
    st.history.append({"role":"assistant","content":ans})
    trim_history(st)

    return ChatRes(answer=ans, products=products, cart=st.cart)

# def chat(req: ChatReq):
#     st = state_for(req.session_id)
#     q = req.query.strip()

#     # ---- LLM decides if we should RAG this turn (conditional, no rigid keywords) ---
#     do_rag = should_rag(q, st.history)

#     products: List[Dict[str, Any]] = []
#     if do_rag:
#         products = text_search(q, k=5)

#         # Fallback: light typo/cleanup normalization if first pass is empty
#         if not products:
#             q2 = re.sub(r"[^a-zA-Z0-9\s]", " ", q)
#             q2 = re.sub(r"\s+", " ", q2).strip()
#             if q2 and q2 != q:
#                 products = text_search(q2, k=5)

#         if products:
#             st.last_results = products[:]

#     # Build context from whatever we found (may be empty if do_rag=False or no hits)
#     context = format_ctx(products)

#     # Include short history so the convo flows naturally
#     ans = llm_answer(context, q, use_history=st.history[-(MEMORY_TURNS-2):])

#     # Track history
#     st.history.append({"role":"user","content":q})
#     st.history.append({"role":"assistant","content":ans})
#     trim_history(st)

#     return ChatRes(answer=ans, products=products, cart=st.cart)


@app.post("/image", response_model=ChatRes)
def image(req: ImageReq):
    st = state_for(req.session_id)

    if req.image_b64:
        # base64 from data URL (drag & drop)
        if req.image_b64.startswith("data:"):
            b64 = dataurl_to_b64(req.image_b64)
        else:
            b64 = req.image_b64
        kwargs = dict(
            near_image=b64,
            target_vector="mm_vec",
            limit=5,
            return_properties=["product_name","description","price","url","image_url", "review_count", "rating_overall", "reviews_json"],
        )
        if MetadataQuery is not None:
            kwargs["return_metadata"] = MetadataQuery(distance=True)
        res = coll.query.near_image(**kwargs)
        products = []
        for o in (res.objects or []):
            p = o.properties
            products.append({
                "product_name": p.get("product_name",""),
                "description":  p.get("description",""),
                "price":        p.get("price",""),
                "url":          p.get("url",""),
                "image_url":    p.get("image_url",""),
                "review_count": p.get("review_count", ""),
                "rating_overall": p.get("rating_overall", ""),
                "reviews_json": p.get("reviews_json")
            })
    elif req.image_url:
        products = image_search(req.image_url, k=5)
    else:
        raise HTTPException(400, "Provide image_b64 (preferred) or image_url")

    st.last_results = products[:]
    context = format_ctx(products)
    ans = llm_answer(context, req.query or "Find similar products", use_history=None)
    st.history.append({"role":"user","content":f"[image] {req.query or 'find similar'}"})
    st.history.append({"role":"assistant","content":ans})
    trim_history(st)
    return ChatRes(answer=ans, products=products, cart=st.cart)

@app.post("/cart/add", response_model=ChatRes)
def cart_add(req: CartAddReq):
    st = state_for(req.session_id)
    m = re.search(r"#?(\d+)$", req.item.strip())
    msg = add_idx(st, int(m.group(1))) if m else add_name(st, req.item)
    st.history.append({"role":"user","content":f"add {req.item}"})
    st.history.append({"role":"assistant","content":msg})
    trim_history(st)
    return ChatRes(answer=msg, products=st.last_results, cart=st.cart)

@app.post("/cart/view", response_model=ChatRes)
def cart_view(req: SessionReq):
    st = state_for(req.session_id)
    msg = view_cart(st)
    st.history.append({"role":"user","content":"view cart"})
    st.history.append({"role":"assistant","content":msg})
    trim_history(st)
    return ChatRes(answer=msg, products=st.last_results, cart=st.cart)

@app.post("/cart/remove", response_model=ChatRes)
def cart_remove(req: CartRemoveReq):
    st = state_for(req.session_id)
    msg = remove_cart(st, req.item)
    st.history.append({"role":"user","content":f"remove {req.item}"})
    st.history.append({"role":"assistant","content":msg})
    trim_history(st)
    return ChatRes(answer=msg, products=st.last_results, cart=st.cart)

@app.post("/cart/checkout", response_model=ChatRes)
def cart_checkout(req: SessionReq):
    st = state_for(req.session_id)
    msg = checkout(st)
    st.history.append({"role":"user","content":"checkout"})
    st.history.append({"role":"assistant","content":msg})
    trim_history(st)
    return ChatRes(answer=msg, products=st.last_results, cart=st.cart)

@app.post("/session/reset", response_model=ChatRes)
def session_reset(req: SessionReq):
    SESSIONS[req.session_id] = SessionState()
    return ChatRes(answer="Session reset.", products=[], cart=[])

