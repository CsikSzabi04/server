# Fordítók és interpreterek
<!-- tech: compilers -->
<!-- aliases: compiler, interpreter, fordítóprogram, parser, lexer, bytecode, vm, jit, típuskövetkeztetés, llvm -->

A fordító (compiler) a forráskódot egy másik reprezentációra (gépi kód, bytecode, másik nyelv) alakítja, az interpreter pedig közvetlenül végrehajtja. A klasszikus lánc: lexer → parser → AST → szemantikai elemzés (scope, típusok) → köztes reprezentáció (IR, gyakran SSA) → optimalizálás → kódgenerálás (regiszter-allokációval) vagy VM/JIT végrehajtás. A gyakorlatban a határ elmosódik: a CPython bytecode-ra fordít és azt interpretálja, a V8 és a JVM interpretálással indul, majd a forró kódot JIT-tel natívra fordítja. Saját DSL-hez, konfigurációs nyelvhez, lekérdezőnyelvhez vagy sablonmotorhoz ugyanezek a technikák kellenek kisebb méretben.

## Lexer (tokenizáló) kézzel írva
<!-- q: Hogyan írjak lexert, ami a forráskódot tokenekre bontja? -->
<!-- tags: lexer, tokenizer, scanner, maximal munch, tokens, source position -->

A lexer a karakterfolyamot tokenekre (szám, azonosító, kulcsszó, operátor, string) bontja, és eldobja a szóközt és a kommenteket. Fontos elv a *maximal munch*: mindig a leghosszabb illeszkedő tokent választjuk, ezért a `>=`-t előbb próbáljuk, mint a `>`-t. Minden tokenhez sor/oszlop pozíciót tárolj, különben később nem tudsz értelmes hibaüzenetet adni. A kulcsszavakat egyszerűbb azonosítóként beolvasni, majd egy halmazból eldönteni, hogy kulcsszó-e.

```python
from dataclasses import dataclass

KEYWORDS = {"let", "fn", "if", "else", "while", "return"}
TWO_CHAR = {"==", "!=", "<=", ">=", "&&", "||"}   # maximal munch: a hosszabbat próbáljuk előbb
SINGLE = set("+-*/%<>=!(){},;")

@dataclass(frozen=True)
class Token:
    kind: str      # NUM, STR, IDENT, KW, OP, EOF
    text: str
    line: int
    col: int

class LexError(Exception):
    pass

def lex(src: str):
    i, line, col = 0, 1, 1
    def at(k=0):   # biztonságos előrenézés: a szöveg végén "\0"-t ad vissza
        return src[i + k] if i + k < len(src) else "\0"
    while True:
        # szóközök és // kommentek átugrása, közben sor/oszlop követése
        while i < len(src) and (at() in " \t\r\n" or (at() == "/" and at(1) == "/")):
            if at() == "/":
                while i < len(src) and at() != "\n":
                    i += 1; col += 1
                continue
            line, col = (line + 1, 1) if at() == "\n" else (line, col + 1)
            i += 1
        if i >= len(src):
            yield Token("EOF", "", line, col)
            return
        start, ch = i, at()
        if ch.isdigit():
            while at().isdigit() or (at() == "." and at(1).isdigit()):
                i += 1
            kind = "NUM"
        elif ch.isalpha() or ch == "_":
            while at().isalnum() or at() == "_":
                i += 1
            kind = "KW" if src[start:i] in KEYWORDS else "IDENT"
        elif ch == '"':
            i += 1
            while at() != '"':
                if at() in "\0\n":
                    raise LexError(f"{line}:{col}: lezáratlan string")
                i += 2 if at() == "\\" else 1     # escape: a következő karaktert is átugorjuk
            i += 1
            kind = "STR"
        elif ch + at(1) in TWO_CHAR:
            i, kind = i + 2, "OP"
        elif ch in SINGLE:
            i, kind = i + 1, "OP"
        else:
            raise LexError(f"{line}:{col}: váratlan karakter {ch!r}")
        yield Token(kind, src[start:i], line, col)
        col += i - start

for tok in lex('let pi = 3.14; // komment\nif (pi >= 3) { print("ok\\n"); }'):
    print(tok.line, tok.col, tok.kind, repr(tok.text))
```

## Rekurzív leszálló (recursive descent) parser
<!-- q: Hogyan írjak rekurzív leszálló parsert egy nyelvtanból? -->
<!-- tags: parser, recursive descent, grammar, EBNF, precedence, left recursion, syntax analysis -->

A rekurzív leszálló parserben a nyelvtan minden szabálya egy függvény, amely a tokeneket fogyasztja és AST-t ad vissza; a precedenciát a szabályok egymásba ágyazása adja (expr → sum → prod → unary → primary). A balrekurzív szabály (`sum := sum "+" prod`) végtelen rekurzióhoz vezetne, ezért ciklussá írjuk át, ami egyben bal-asszociativitást ad. Ez a legelterjedtebb technika éles fordítókban is (GCC, Clang, Go, Rust), mert jól olvasható és kiváló hibaüzeneteket lehet vele adni. Ahol két token előrenézés kell (értékadás vs. kifejezés), ott `peek(1)`-gyel döntünk.

```python
import re

# Nyelvtan (EBNF) — minden szabályból egy metódus lesz:
#   program  := stmt* EOF
#   stmt     := "let" ID "=" expr ";" | ID "=" expr ";" | "while" "(" expr ")" block | expr ";"
#   block    := "{" stmt* "}"
#   expr     := additive (("<" | "==") additive)*
#   additive := term (("+" | "-") term)*
#   term     := unary (("*" | "/") unary)*
#   unary    := "-" unary | primary
#   primary  := NUM | ID | ID "(" args? ")" | "(" expr ")"
TOKEN = re.compile(r"\s*(?:(\d+)|([A-Za-z_]\w*)|(==|[-+*/<=(){};,]))")

def tokenize(src):
    toks, pos, src = [], 0, src.rstrip()
    while pos < len(src):
        m = TOKEN.match(src, pos)
        if not m:
            raise SyntaxError(f"hibás karakter a(z) {pos}. pozíción")
        num, name, op = m.groups()
        toks.append(int(num) if num else name or op)
        pos = m.end()
    return toks + ["<eof>"]

class Parser:
    def __init__(self, src): self.t, self.i = tokenize(src), 0
    def peek(self, k=0): return self.t[self.i + k]
    def eat(self, *alts):                      # ha illeszkedik, elfogyasztja és visszaadja
        if self.peek() in alts: self.i += 1; return self.t[self.i - 1]
        return None
    def expect(self, tok):
        if self.eat(tok) is None: raise SyntaxError(f"{tok!r} várt, de {self.peek()!r} jött")
    def name(self):
        tok = self.peek()
        if not (isinstance(tok, str) and tok.isidentifier()): raise SyntaxError(f"név várt: {tok!r}")
        self.i += 1; return tok

    def program(self):
        stmts = []
        while self.peek() != "<eof>": stmts.append(self.stmt())
        return ("block", stmts)
    def block(self):
        self.expect("{"); stmts = []
        while not self.eat("}"): stmts.append(self.stmt())
        return ("block", stmts)
    def stmt(self):
        if self.eat("let"):
            n = self.name(); self.expect("="); e = self.expr(); self.expect(";"); return ("let", n, e)
        if self.eat("while"):
            self.expect("("); c = self.expr(); self.expect(")"); return ("while", c, self.block())
        if isinstance(self.peek(), str) and self.peek().isidentifier() and self.peek(1) == "=":
            n = self.name(); self.i += 1; e = self.expr(); self.expect(";"); return ("set", n, e)
        e = self.expr(); self.expect(";"); return ("expr", e)

    def binary(self, sub, ops):                # balrekurzió helyett ciklus => bal-asszociatív
        left = sub()
        while (op := self.eat(*ops)) is not None: left = ("bin", op, left, sub())
        return left
    def expr(self):     return self.binary(self.additive, ("<", "=="))
    def additive(self): return self.binary(self.term, ("+", "-"))
    def term(self):     return self.binary(self.unary, ("*", "/"))
    def unary(self):    return ("neg", self.unary()) if self.eat("-") else self.primary()
    def primary(self):
        if isinstance(self.peek(), int): self.i += 1; return ("num", self.t[self.i - 1])
        if self.eat("("): e = self.expr(); self.expect(")"); return e
        n = self.name()
        if not self.eat("("): return ("var", n)
        args = []
        while not self.eat(")"):
            args.append(self.expr()); self.eat(",")
        return ("call", n, args)

print(Parser("let n = 10; while (0 < n) { n = n - 1; } print(n * -2, 8 - 4 - 2);").program())
```

## Pratt parser (operátor-precedencia kötési erőkkel)
<!-- q: Mi az a Pratt parser és hogyan kezeli az operátor precedenciát? -->
<!-- tags: pratt parser, binding power, operator precedence, top down operator precedence, associativity -->

A Pratt parser minden operátorhoz egy bal és jobb *kötési erőt* (binding power) rendel, és egyetlen ciklusban dönti el, hogy az operátor a bal oldali kifejezéshez kötődik-e. A bal-asszociativitás `(bal < jobb)`, a jobb-asszociativitás `(bal > jobb)` kötési erővel adható meg, így új operátor felvétele csak egy táblázatsor, nem egy új nyelvtani szint. Prefix (`-x`), infix (`a + b`), postfix (`n!`) és mixfix (`c ? a : b`) operátorok egységesen kezelhetők; ezért szeretik a JS- és Rust-eszközök (rust-analyzer, esbuild). A kimenet itt S-kifejezés, ami teszteléshez kényelmes.

```python
import re

PREFIX_BP = {"-": 9, "+": 9}
POSTFIX_BP = {"!": 11}
INFIX_BP = {                     # (bal, jobb): bal < jobb => bal-asszociatív
    "?": (2, 1),                 # ternary, jobb-asszociatív: a ? b : c ? d : e
    "+": (3, 4), "-": (3, 4),
    "*": (5, 6), "/": (5, 6),
    "^": (8, 7),                 # hatványozás jobb-asszociatív: 2^3^2 = 2^(3^2)
}

class Pratt:
    def __init__(self, src):
        self.toks = re.findall(r"\d+|[A-Za-z_]\w*|[-+*/^!?:()]", src) + ["<eof>"]
        self.i = 0
    def peek(self): return self.toks[self.i]
    def next(self):
        self.i += 1
        return self.toks[self.i - 1]

    def parse(self, min_bp=0):
        tok = self.next()
        # 1) prefix ("nud") rész: mivel kezdődhet egy kifejezés?
        if tok.isdigit() or tok.isidentifier():
            lhs = tok
        elif tok == "(":
            lhs = self.parse(0)
            if self.next() != ")": raise SyntaxError("hiányzó ')'")
        elif tok in PREFIX_BP:
            lhs = f"({tok} {self.parse(PREFIX_BP[tok])})"
        else:
            raise SyntaxError(f"váratlan token: {tok}")
        # 2) infix/postfix ("led") ciklus: amíg az operátor elég erősen köt
        while (op := self.peek()) not in ("<eof>", ")", ":"):
            if op in POSTFIX_BP:
                if POSTFIX_BP[op] < min_bp: break
                self.next(); lhs = f"({op} {lhs})"
                continue
            if op not in INFIX_BP: raise SyntaxError(f"ismeretlen operátor: {op}")
            l_bp, r_bp = INFIX_BP[op]
            if l_bp < min_bp: break          # a hívó szint erősebben köt -> visszaadjuk lhs-t
            self.next()
            if op == "?":
                mid = self.parse(0)
                if self.next() != ":": raise SyntaxError("hiányzó ':'")
                lhs = f"(? {lhs} {mid} {self.parse(r_bp)})"
            else:
                lhs = f"({op} {lhs} {self.parse(r_bp)})"
        return lhs

for src in ["1 + 2 * 3", "2 ^ 3 ^ 2", "-a!", "(1 + 2) * x", "a ? b : c ? d : e", "8 - 4 - 2"]:
    print(f"{src:20} => {Pratt(src).parse()}")
# 1 + 2 * 3 => (+ 1 (* 2 3)),  2 ^ 3 ^ 2 => (^ 2 (^ 3 2)),  8 - 4 - 2 => (- (- 8 4) 2)
```

## AST tervezése és a visitor minta
<!-- q: Hogyan tervezzek absztrakt szintaxisfát (AST) és hogyan járjam be? -->
<!-- tags: ast, abstract syntax tree, visitor pattern, pattern matching, immutable tree, source span -->

Az AST a program szerkezetét írja le a szintaktikai zaj (zárójelek, pontosvesszők) nélkül; minden csomóponttípus egy osztály. Érdemes immutábilis csomópontokat használni (`frozen=True`), mert a transzformációk (optimalizálás, átnevezés) így új fát építenek, és a változatlan részfák megoszthatók. A forrás-pozíciót (`span`) tárold el, de hagyd ki az egyenlőség-vizsgálatból, különben két azonos kifejezés más helyen „különböző” lesz. Bejárásra a klasszikus *visitor* vagy Python 3.10+ alatt a `match` mintaillesztés a legolvashatóbb.

```python
from __future__ import annotations
from dataclasses import dataclass, field, replace

@dataclass(frozen=True, slots=True)
class Span:                          # forrás-pozíció a hibaüzenetekhez
    line: int
    col: int

@dataclass(frozen=True, slots=True)
class Num:
    value: float
    span: Span | None = field(default=None, compare=False)

@dataclass(frozen=True, slots=True)
class Var:
    name: str
    span: Span | None = field(default=None, compare=False)

@dataclass(frozen=True, slots=True)
class BinOp:
    op: str
    left: Num | Var | BinOp
    right: Num | Var | BinOp
    span: Span | None = field(default=None, compare=False)

class Visitor:
    """Klasszikus visitor: a csomópont osztálynevére dispatch-el (visit_Num, visit_Var...)."""
    def visit(self, node):
        return getattr(self, f"visit_{type(node).__name__}", self.generic)(node)
    def generic(self, node):
        raise NotImplementedError(type(node).__name__)

class Printer(Visitor):
    def visit_Num(self, n): return str(n.value)
    def visit_Var(self, v): return v.name
    def visit_BinOp(self, b): return f"({self.visit(b.left)} {b.op} {self.visit(b.right)})"

def free_vars(node) -> set[str]:
    # Ugyanez mintaillesztéssel, visitor osztály nélkül
    match node:
        case Num(): return set()
        case Var(name=n): return {n}
        case BinOp(left=l, right=r): return free_vars(l) | free_vars(r)
    raise TypeError(node)

def rename(node, old: str, new: str):
    # Immutábilis transzformáció: csak a megváltozott útvonalat másoljuk le
    match node:
        case Var(name=n) if n == old:
            return replace(node, name=new)
        case BinOp():
            l, r = rename(node.left, old, new), rename(node.right, old, new)
            return node if (l is node.left and r is node.right) else replace(node, left=l, right=r)
        case _:
            return node

tree = BinOp("*", Num(2), BinOp("+", Var("x", Span(1, 6)), Num(3)))
print(Printer().visit(tree))                     # (2 * (x + 3))
print(free_vars(tree))                           # {'x'}
print(Printer().visit(rename(tree, "x", "y")))   # (2 * (y + 3))
print(tree == BinOp("*", Num(2), BinOp("+", Var("x"), Num(3))))  # True: a span nem számít
```

## Tree-walking interpreter környezetekkel és closure-ökkel
<!-- q: Hogyan működik egy fabejáró interpreter, és hogyan valósítok meg closure-t? -->
<!-- tags: interpreter, tree walking, environment, scope chain, closure, lexical scoping, return -->

A fabejáró interpreter rekurzívan kiértékeli az AST csomópontjait; a változókat egymásba láncolt *környezetek* (Env) tárolják, a keresés a láncon felfelé halad — ez a lexikális scope. A closure a függvénytörzs mellett a *definiáláskori* környezetet is eltárolja, ezért a belső függvény akkor is eléri a külső változókat, amikor a külső függvény már visszatért. A `return`-t legegyszerűbb kivétellel megvalósítani, ami felfelé „kiugrik” a beágyazott blokkokból. Egyszerű és jól debugolható, de lassú (sok pointer-követés, dispatch minden csomóponton) — ezért térnek át a komolyabb nyelvek bytecode VM-re.

```python
class Env:
    def __init__(self, parent=None):
        self.vars, self.parent = {}, parent
    def find(self, name):
        env = self
        while env is not None:                 # lexikális scope: felfelé a láncon
            if name in env.vars: return env
            env = env.parent
        raise NameError(f"nem definiált: {name}")

class ReturnSignal(Exception):                 # a 'return' kivételként ugrik ki a blokkokból
    def __init__(self, value): self.value = value

class Closure:
    def __init__(self, params, body, env):
        self.params, self.body, self.env = params, body, env  # a DEFINIÁLÁSKORI env-et őrzi

OPS = {"+": lambda a, b: a + b, "-": lambda a, b: a - b,
       "*": lambda a, b: a * b, "<": lambda a, b: a < b}

def ev(node, env):
    tag = node[0]
    if tag == "num": return node[1]
    if tag == "var": return env.find(node[1]).vars[node[1]]
    if tag == "bin": return OPS[node[1]](ev(node[2], env), ev(node[3], env))
    if tag == "let": env.vars[node[1]] = ev(node[2], env); return None
    if tag == "set": env.find(node[1]).vars[node[1]] = ev(node[2], env); return None
    if tag == "if":
        branch = node[2] if ev(node[1], env) else node[3]
        return ev(branch, env) if branch else None
    if tag == "while":
        while ev(node[1], env): ev(node[2], env)
        return None
    if tag == "block":
        inner, result = Env(env), None        # minden blokk új scope
        for stmt in node[1]: result = ev(stmt, inner)
        return result
    if tag == "fn": return Closure(node[1], node[2], env)
    if tag == "return": raise ReturnSignal(ev(node[1], env))
    if tag == "call":
        fn = ev(node[1], env)
        frame = Env(fn.env)                    # a hívási keret szülője a closure env-je!
        frame.vars.update(zip(fn.params, [ev(a, env) for a in node[2]]))
        try:
            return ev(fn.body, frame)
        except ReturnSignal as r:
            return r.value
    raise ValueError(f"ismeretlen csomópont: {tag}")

# fn make_counter() { let n = 0; return fn() { n = n + 1; return n; }; }
program = ("block", [
    ("let", "make_counter", ("fn", [], ("block", [
        ("let", "n", ("num", 0)),
        ("return", ("fn", [], ("block", [
            ("set", "n", ("bin", "+", ("var", "n"), ("num", 1))),
            ("return", ("var", "n"))])))]))),
    ("let", "c", ("call", ("var", "make_counter"), [])),
    ("call", ("var", "c"), []),
    ("call", ("var", "c"), []),
])
print(ev(program, Env()))   # 2 — a closure megőrizte n állapotát a hívások között
```

## Teljes mini nyelv 1. rész: egymenetes bytecode-fordító
<!-- q: Hogyan fordítsak egy kis nyelvet bytecode-ra lexerrel és parserrel együtt? -->
<!-- tags: bytecode compiler, single pass compiler, backpatching, precedence climbing, code generation, jumps -->

Ez és a következő szakasz együtt egy teljes kis nyelv: változók, aritmetika, összehasonlítás, `while`, `if/else`, `print`. A fordító *egymenetes* (mint a Lua vagy a clox): parse közben azonnal bytecode-ot emittál, külön AST nélkül. A még ismeretlen ugrási célokat *backpatching*-gel töltjük ki: előbb `None` céllal emittáljuk az ugrást, és a blokk vége után írjuk bele a valódi címet. A változók névből slot-indexet kapnak fordítási időben, így futáskor nincs szótárkeresés.

```python
import re

TOKEN_RX = re.compile(r"\s*(?:(?P<num>\d+)|(?P<id>[A-Za-z_]\w*)|(?P<op>==|!=|<=|>=|[-+*/%<>=(){};]))")
KEYWORDS = {"let", "while", "if", "else", "print"}
PREC = {"==": 1, "!=": 1, "<": 2, ">": 2, "<=": 2, ">=": 2, "+": 3, "-": 3, "*": 4, "/": 4, "%": 4}

def lex(src):
    toks, pos, src = [], 0, src.strip()
    while pos < len(src):
        m = TOKEN_RX.match(src, pos)
        if not m: raise SyntaxError(f"hibás karakter: {src[pos]!r}")
        kind = m.lastgroup
        toks.append((kind, int(m.group(kind)) if kind == "num" else m.group(kind)))
        pos = m.end()
    return toks + [("eof", None)]

class Compiler:
    def __init__(self, src):
        self.toks, self.i, self.code, self.slots = lex(src), 0, [], {}
    def peek(self): return self.toks[self.i][1]
    def take(self):
        self.i += 1; return self.toks[self.i - 1]
    def expect(self, text):
        if self.take()[1] != text: raise SyntaxError(f"{text!r} várt a(z) {self.i}. tokennél")
    def emit(self, *ins):
        self.code.append(list(ins)); return len(self.code) - 1
    def patch(self, at):                       # backpatching: az ugrás célja = a jelenlegi vég
        self.code[at][1] = len(self.code)
    def slot(self, name):
        if name not in self.slots: raise NameError(f"nem deklarált változó: {name}")
        return self.slots[name]

    def program(self):
        while self.toks[self.i][0] != "eof": self.stmt()
        self.emit("HALT"); return self.code
    def block(self):
        self.expect("{")
        while self.peek() != "}": self.stmt()
        self.take()
    def stmt(self):
        word = self.peek()
        if word == "let":
            self.take(); _, name = self.take(); self.expect("="); self.expr(0); self.expect(";")
            self.emit("STORE", self.slots.setdefault(name, len(self.slots)))
        elif word == "print":
            self.take(); self.expr(0); self.expect(";"); self.emit("PRINT")
        elif word == "while":
            self.take(); loop_start = len(self.code)
            self.expect("("); self.expr(0); self.expect(")")
            exit_jump = self.emit("JUMP_IF_FALSE", None)   # cél még ismeretlen
            self.block(); self.emit("JUMP", loop_start); self.patch(exit_jump)
        elif word == "if":
            self.take(); self.expect("("); self.expr(0); self.expect(")")
            else_jump = self.emit("JUMP_IF_FALSE", None); self.block()
            if self.peek() == "else":
                self.take(); end_jump = self.emit("JUMP", None)
                self.patch(else_jump); self.block(); self.patch(end_jump)
            else:
                self.patch(else_jump)
        else:                                  # értékadás: név = kifejezés;
            _, name = self.take(); self.expect("="); self.expr(0); self.expect(";")
            self.emit("STORE", self.slot(name))
    def expr(self, min_prec):                  # precedence climbing
        self.atom()
        while self.peek() in PREC and PREC[self.peek()] > min_prec:
            op = self.take()[1]
            self.expr(PREC[op])                # szigorúan nagyobb => bal-asszociatív
            self.emit("BINOP", op)
    def atom(self):
        kind, val = self.take()
        if kind == "num": self.emit("CONST", val)
        elif kind == "id" and val not in KEYWORDS: self.emit("LOAD", self.slot(val))
        elif val == "(": self.expr(0); self.expect(")")
        elif val == "-": self.atom(); self.emit("NEG")
        else: raise SyntaxError(f"váratlan token: {val!r}")
```

## Teljes mini nyelv 2. rész: stack-alapú virtuális gép
<!-- q: Hogyan működik egy stack-alapú bytecode virtuális gép? -->
<!-- tags: virtual machine, stack vm, bytecode, dispatch loop, interpreter loop, program counter, disassembler -->

A stack-alapú VM operandusai egy veremben vannak: a `CONST`/`LOAD` rátesz, a `BINOP` levesz kettőt és visszatesz egyet, így az utasítások rövidek és a kódgenerálás egyszerű (posztorder bejárás). A végrehajtó ciklus a *dispatch loop*: kiolvassa az utasítást a `pc` (program counter) helyéről, és elágazik az opkódra — valódi VM-ekben ez `switch` vagy „computed goto”, ez a fő teljesítmény-szűk keresztmetszet. A regiszter-alapú VM (Lua 5, Dalvik) kevesebb utasítással dolgozik, de bonyolultabb a fordítója. Mindig írj diszasszemblert, mert a bytecode-hibákat csak így lehet hatékonyan keresni.

```python
import operator
# Az előző szakasz Compiler osztályát használja.

BINOPS = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.floordiv,
          "%": operator.mod, "<": operator.lt, ">": operator.gt, "<=": operator.le,
          ">=": operator.ge, "==": operator.eq, "!=": operator.ne}

def run(code, n_slots, out=print):
    stack, slots, pc = [], [0] * n_slots, 0
    while True:                                 # dispatch loop
        op, *args = code[pc]
        pc += 1
        if op == "CONST":   stack.append(args[0])
        elif op == "LOAD":  stack.append(slots[args[0]])
        elif op == "STORE": slots[args[0]] = stack.pop()
        elif op == "BINOP":
            b = stack.pop(); a = stack.pop()    # sorrend számít: a jobb operandus van felül
            stack.append(int(BINOPS[args[0]](a, b)))
        elif op == "NEG":   stack.append(-stack.pop())
        elif op == "PRINT": out(stack.pop())
        elif op == "JUMP":  pc = args[0]
        elif op == "JUMP_IF_FALSE":
            if not stack.pop(): pc = args[0]
        elif op == "HALT":  return slots
        else: raise RuntimeError(f"ismeretlen opkód: {op}")

SOURCE = """
let n = 10; let a = 0; let b = 1;
while (n > 0) { print(a); let t = a + b; a = b; b = t; n = n - 1; }
if (a % 2 == 0) { print(1); } else { print(0); }
"""
compiler = Compiler(SOURCE)
bytecode = compiler.program()
for addr, ins in enumerate(bytecode):          # diszasszembler: cím + utasítás
    print(f"{addr:3}  {ins[0]:<14} {' '.join(map(str, ins[1:]))}")
run(bytecode, len(compiler.slots))             # 0 1 1 2 3 5 8 13 21 34, majd 0 (55 páratlan)
```

## Statikus típusellenőrzés
<!-- q: Hogyan írjak statikus típusellenőrzőt egy kis nyelvhez? -->
<!-- tags: type checking, static typing, type checker, function types, semantic analysis, type error -->

A típusellenőrző fordítási időben bejárja az AST-t, és minden kifejezéshez kiszámolja a típusát egy típuskörnyezet (név → típus) alapján; ha egy operátor vagy hívás nem illik a típusokhoz, hibát jelez, mielőtt a program futna. A függvénytípus a paraméterek és a visszatérési érték típusából áll, híváskor az argumentumszámot és minden argumentum típusát ellenőrizni kell. Az `if` ágainak azonos típusúnak kell lenniük, ha kifejezésként használjuk. A jó hibaüzenet tartalmazza, mit vártunk és mit kaptunk — ez a típusrendszer felhasználói felülete.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class FnType:
    params: tuple
    ret: object
    def __str__(self): return f"({', '.join(map(str, self.params))}) -> {self.ret}"

INT, BOOL = "int", "bool"

class TypeCheckError(Exception):
    pass

def check(e, env):
    tag = e[0]
    if tag == "int": return INT
    if tag == "bool": return BOOL
    if tag == "var":
        if e[1] not in env: raise TypeCheckError(f"ismeretlen változó: {e[1]}")
        return env[e[1]]
    if tag == "bin":
        op, lt, rt = e[1], check(e[2], env), check(e[3], env)
        if op in ("+", "-", "*") and lt == rt == INT: return INT
        if op == "<" and lt == rt == INT: return BOOL
        if op == "==" and lt == rt: return BOOL
        if op in ("&&", "||") and lt == rt == BOOL: return BOOL
        raise TypeCheckError(f"'{op}' nem alkalmazható: {lt} és {rt}")
    if tag == "if":
        if check(e[1], env) != BOOL: raise TypeCheckError("az if feltétele bool kell legyen")
        t1, t2 = check(e[2], env), check(e[3], env)
        if t1 != t2: raise TypeCheckError(f"az ágak típusa eltér: {t1} vs {t2}")
        return t1
    if tag == "let":                         # ("let", név, érték, törzs)
        return check(e[3], {**env, e[1]: check(e[2], env)})
    if tag == "lambda":                      # ("lambda", [(név, típus)], visszatérési típus, törzs)
        body_t = check(e[3], {**env, **dict(e[1])})
        if body_t != e[2]: raise TypeCheckError(f"a törzs típusa {body_t}, de {e[2]} a deklarált")
        return FnType(tuple(t for _, t in e[1]), e[2])
    if tag == "call":
        ft = check(e[1], env)
        if not isinstance(ft, FnType): raise TypeCheckError(f"nem függvény: {ft}")
        args = [check(a, env) for a in e[2]]
        if len(args) != len(ft.params):
            raise TypeCheckError(f"{len(ft.params)} argumentum várt, {len(args)} kapott")
        for i, (want, got) in enumerate(zip(ft.params, args), 1):
            if want != got: raise TypeCheckError(f"{i}. argumentum: {want} várt, {got} kapott")
        return ft.ret
    raise ValueError(tag)

inc = ("lambda", [("x", INT)], INT, ("bin", "+", ("var", "x"), ("int", 1)))
print(check(inc, {}))                                          # (int) -> int
print(check(("let", "inc", inc, ("call", ("var", "inc"), [("int", 41)])), {}))  # int
try:
    check(("call", inc, [("bool", True)]), {})
except TypeCheckError as err:
    print("típushiba:", err)                                   # 1. argumentum: int várt, bool kapott
```

## Típuskövetkeztetés: Hindley–Milner és unifikáció
<!-- q: Hogyan működik a Hindley–Milner típuskövetkeztetés és az unifikáció? -->
<!-- tags: type inference, hindley milner, algorithm w, unification, occurs check, let polymorphism, generalization -->

A Hindley–Milner (HM) rendszer annotációk nélkül következteti ki a legáltalánosabb típust: minden ismeretlenhez friss típusváltozót rendel, a használatból egyenlőségi kényszereket gyűjt, és ezeket *unifikációval* oldja meg. Az *occurs check* megakadályozza a végtelen típust (pl. `x x` esetén `t = t -> r`). A `let`-nél a típust *általánosítjuk* (∀a. a → a), és minden használatkor friss változókkal *példányosítjuk* — ez a let-polimorfizmus, ezért lehet `id`-t egyszerre több típussal hívni. Ezen alapul az OCaml, a Haskell és részben a Rust/F# következtetése; a lambda-paraméterek viszont monomorfak maradnak.

```python
import itertools
from dataclasses import dataclass

@dataclass(frozen=True)
class TVar: name: str
@dataclass(frozen=True)
class TCon: name: str; args: tuple = ()

INT, BOOL = TCon("Int"), TCon("Bool")
counter = itertools.count()
def fn(a, b): return TCon("->", (a, b))
def fresh(): return TVar(f"t{next(counter)}")

def apply(s, t):                      # helyettesítés alkalmazása (a láncokat is követi)
    if isinstance(t, TVar): return apply(s, s[t.name]) if t.name in s else t
    return TCon(t.name, tuple(apply(s, a) for a in t.args))

def ftv(t):                           # szabad típusváltozók halmaza
    return {t.name} if isinstance(t, TVar) else set().union(*map(ftv, t.args))

def unify(a, b, s):
    a, b = apply(s, a), apply(s, b)
    if a == b: return s
    if isinstance(b, TVar): a, b = b, a
    if isinstance(a, TVar):
        if a.name in ftv(b): raise TypeError(f"végtelen típus: {a.name} ~ {b}")  # occurs check
        return {**s, a.name: b}
    if a.name != b.name or len(a.args) != len(b.args): raise TypeError(f"ütközés: {a} vs {b}")
    for x, y in zip(a.args, b.args): s = unify(x, y, s)
    return s

def generalize(env, t, s):            # séma = (kvantált változók, típus), pl. ∀a. a -> a
    in_env = set().union(*(ftv(apply(s, st)) - set(vs) for vs, st in env.values()))
    return tuple(ftv(apply(s, t)) - in_env), apply(s, t)

def instantiate(scheme):              # minden kvantált változó helyére friss változó
    vs, t = scheme
    return apply({v: fresh() for v in vs}, t)

def infer(env, e, s):                 # Algorithm W: (típus, helyettesítés)
    tag = e[0]
    if tag == "lit": return (BOOL if isinstance(e[1], bool) else INT), s
    if tag == "var": return instantiate(env[e[1]]), s
    if tag == "lam":
        tv = fresh()
        body, s = infer({**env, e[1]: ((), tv)}, e[2], s)    # a paraméter NEM polimorf
        return fn(tv, body), s
    if tag == "app":
        f, s = infer(env, e[1], s); a, s = infer(env, e[2], s); r = fresh()
        return r, unify(f, fn(a, r), s)
    if tag == "let":                  # let-polimorfizmus: itt általánosítunk
        v, s = infer(env, e[2], s)
        return infer({**env, e[1]: generalize(env, v, s)}, e[3], s)
    raise ValueError(tag)

def show(t, names):
    if isinstance(t, TVar): return names.setdefault(t.name, "'" + chr(97 + len(names)))
    if t.name == "->": return f"({show(t.args[0], names)} -> {show(t.args[1], names)})"
    return t.name

def type_of(e):
    t, s = infer({}, e, {})
    return show(apply(s, t), {})

ident = ("lam", "x", ("var", "x"))
compose = ("lam", "f", ("lam", "g", ("lam", "x", ("app", ("var", "f"), ("app", ("var", "g"), ("var", "x"))))))
print(type_of(ident))      # ('a -> 'a)
print(type_of(compose))    # (('a -> 'b) -> (('c -> 'a) -> ('c -> 'b)))
print(type_of(("let", "id", ident, ("app", ("app", ("var", "id"), ("var", "id")), ("lit", 1)))))  # Int
try:
    type_of(("lam", "x", ("app", ("var", "x"), ("var", "x"))))
except TypeError as err:
    print("hiba:", err)     # végtelen típus
```

## Köztes reprezentáció: háromcímes kód és SSA
<!-- q: Mi az SSA forma és mire jó a phi függvény? -->
<!-- tags: ssa, static single assignment, phi node, three address code, ir, intermediate representation, cfg -->

A háromcímes kód (TAC) minden utasítása legfeljebb egy műveletet végez (`t3 = t1 + t2`), és alapblokkokba, azokból vezérlésfolyam-gráfba (CFG) szerveződik. SSA formában minden változónak pontosan *egy* definíciója van: az újradefiniálás új verziót kap (`x_0`, `x_1`), így a def-use láncok triviálisak, és a konstans-propagáció, DCE, GVN egyszerűbb és gyorsabb. Ahol több ág találkozik, a `phi` függvény választ az érkezési iránynak megfelelő verzió közül. Éles fordítók a phi-ket dominancia-határok (dominance frontier, Cytron-algoritmus) alapján helyezik el; az alábbi példa egy egyszerű elágazás (diamond) esetét mutatja.

```python
class SSABuilder:
    def __init__(self):
        self.counter = {}                          # változó -> következő szabad verziószám

    def new(self, var):
        n = self.counter.get(var, 0)
        self.counter[var] = n + 1
        return f"{var}_{n}"

    def block(self, instrs, current):
        """Egy alapblokk átnevezése; current: változó -> aktuális SSA név."""
        current, out = dict(current), []
        for dst, op, a, b in instrs:
            # FONTOS sorrend: előbb az operandusok (régi verzió), utána az új definíció
            a, b = (current.get(x, x) if isinstance(x, str) else x for x in (a, b))
            current[dst] = self.new(dst)
            out.append((current[dst], op, a, b))
        return out, current

def diamond(entry, then_, else_, after):
    """entry -> (then | else) -> join[phi] -> after"""
    b = SSABuilder()
    e_code, cur = b.block(entry, {})
    t_code, t_cur = b.block(then_, cur)
    f_code, f_cur = b.block(else_, cur)
    phis, join = [], dict(cur)
    for var in sorted(set(t_cur) | set(f_cur)):
        tv, fv = t_cur.get(var), f_cur.get(var)
        if tv != fv:                               # csak ott kell phi, ahol az ágak eltérnek
            join[var] = b.new(var)
            phis.append((join[var], "phi", tv, fv))
    a_code, _ = b.block(after, join)
    return {"entry": e_code, "then": t_code, "else": f_code, "join": phis + a_code}

# x = a + 1; if (x < 10) { y = x * 2 } else { y = x - 1; x = 0 }; z = x + y
ssa = diamond(
    entry=[("x", "add", "a", 1)],
    then_=[("y", "mul", "x", 2)],
    else_=[("y", "sub", "x", 1), ("x", "const", 0, None)],
    after=[("z", "add", "x", "y")],
)
for name, code in ssa.items():
    print(name, code)
# join: x_2 = phi(x_0, x_1), y_2 = phi(y_0, y_1), z_0 = x_2 + y_2
```

## Konstans hajtogatás és propagáció
<!-- q: Hogyan működik a constant folding és a konstans propagáció optimalizáció? -->
<!-- tags: constant folding, constant propagation, optimization, ast transformer, python ast -->

A *constant folding* fordítási időben kiszámolja a csak konstansokból álló kifejezéseket (`60 * 60` → `3600`), a *propagáció* pedig az ismert értékű változókat behelyettesíti, ami újabb hajtogatást tesz lehetővé. Posztorder bejárás kell: előbb a gyerekeket hajtogatjuk, utána a szülőt. Futásidejű hibát (nullával osztás) nem szabad fordítási hibává vagy eltűnő kóddá alakítani, és a hatalmas eredményeket (`2 ** 10**9`) sem érdemes beégetni. Ciklusban és elágazás után a „változó = konstans” tudás érvénytelenné válhat, ezért ott konzervatívan el kell felejteni (SSA-ban ez a probléma eltűnik, lásd SCCP). Az algebrai azonosságok (`x + 0 → x`) dinamikus nyelvben csak típusinformációval biztonságosak (stringre `+ 0` hibát dob).

```python
import ast
import operator

BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}

class ConstFolder(ast.NodeTransformer):
    """Konstans hajtogatás + propagáció egyenes vonalú Python kódra."""
    def __init__(self):
        self.known = {}                                # név -> ismert konstans érték

    def visit_Assign(self, node):
        node.value = self.visit(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                if isinstance(node.value, ast.Constant):
                    self.known[target.id] = node.value.value
                else:
                    self.known.pop(target.id, None)   # felülírták ismeretlennel
        return node

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id in self.known:
            return ast.copy_location(ast.Constant(self.known[node.id]), node)
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)                      # posztorder: előbb a gyerekek
        l, r, op = node.left, node.right, type(node.op)
        if isinstance(l, ast.Constant) and isinstance(r, ast.Constant) and op in BIN:
            try:
                value = BIN[op](l.value, r.value)
            except (ZeroDivisionError, OverflowError, TypeError):
                return node                           # a futásidejű hibát meghagyjuk
            if not (isinstance(value, int) and value.bit_length() > 64):
                return ast.copy_location(ast.Constant(value), node)
        return node

    def visit_For(self, node):
        # Konzervatív: ciklus/elágazás előtt mindent elfelejtünk, a törzset nem bántjuk
        self.known.clear()
        return node
    visit_While = visit_If = visit_For

src = """
width = 60 * 60
height = width // 2 + 3 * 4
area = width * height
for i in range(3):
    area = area + i
print(area, height % 7, 1 // 0)
"""
tree = ast.fix_missing_locations(ConstFolder().visit(ast.parse(src)))
print(ast.unparse(tree))
# width = 3600 / height = 1812 / area = 6523200 / a for után semmit sem propagálunk:
# print(area, height % 7, 1 // 0) változatlan marad (konzervatív, de helyes)
```

## Halott kód eliminálás és liveness-analízis
<!-- q: Hogyan működik a dead code elimination és a liveness analízis? -->
<!-- tags: dead code elimination, dce, liveness analysis, dataflow analysis, fixpoint, cfg, side effects -->

Egy változó *élő* (live) egy pontban, ha az értékét később még olvashatja a program; a liveness visszafelé haladó adatfolyam-analízis: `in = (out − def) ∪ use`, és `out` a rákövetkező blokkok `in`-jeinek uniója, fixpontig iterálva (ciklusok miatt). Az a mellékhatás-mentes értékadás, amelynek célja nem élő, *halott kód*, és törölhető. A törlés újabb kódot tehet halottá (lánc), ezért az egészet ismételni kell, amíg változik. Mellékhatásos utasítást (hívás, store, I/O) soha ne törölj csak azért, mert az eredményét senki sem olvassa.

```python
SIDE_EFFECTS = {"call", "print", "store", "ret", "br"}

def uses(ins): return {x for x in ins[2] if isinstance(x, str)}
def defs(ins): return {ins[0]} if ins[0] else set()

def liveness(cfg, succ):
    """Visszafelé haladó adatfolyam-analízis fixpontig."""
    live_in = {b: set() for b in cfg}
    live_out = {b: set() for b in cfg}
    changed = True
    while changed:
        changed = False
        for b in reversed(list(cfg)):              # fordított sorrend: gyorsabb konvergencia
            out = set().union(*(live_in[s] for s in succ[b]))
            inn = set(out)
            for ins in reversed(cfg[b]):
                inn = (inn - defs(ins)) | uses(ins)
            if inn != live_in[b] or out != live_out[b]:
                live_in[b], live_out[b], changed = inn, out, True
    return live_in, live_out

def dce(cfg, succ):
    while True:                                    # a törlés újabb halott kódot szülhet
        _, live_out = liveness(cfg, succ)
        removed = 0
        for b, code in cfg.items():
            live, kept = set(live_out[b]), []
            for ins in reversed(code):
                if ins[0] and ins[0] not in live and ins[1] not in SIDE_EFFECTS:
                    removed += 1                   # halott, mellékhatás-mentes értékadás
                    continue
                live = (live - defs(ins)) | uses(ins)
                kept.append(ins)
            cfg[b] = kept[::-1]
        if not removed:
            return cfg

# Utasítás: (cél vagy None, művelet, operandusok)
cfg = {
    "entry": [("a", "const", (1,)), ("b", "add", ("a", 2)), ("t", "mul", ("b", "b")),
              (None, "br", ())],
    "loop":  [("u", "add", ("t", 1)), ("a", "add", ("a", 1)), ("c", "lt", ("a", 10)),
              (None, "br", ("c",))],
    "exit":  [(None, "print", ("a",))],
}
succ = {"entry": ["loop"], "loop": ["loop", "exit"], "exit": []}
for block, code in dce(cfg, succ).items():
    print(block, code)     # u, majd t és b is eltűnik; a, c és a print marad
```

## Közös részkifejezések (CSE) és inlining
<!-- q: Hogyan működik a common subexpression elimination és a függvény inlining? -->
<!-- tags: cse, common subexpression elimination, value numbering, inlining, optimization, commutativity -->

A *local value numbering* (LVN) minden kiszámolt értékhez egy számot rendel; ha egy `(op, vn1, vn2)` hármas már szerepelt, és a tartó változót azóta nem írták felül, a számítás másolásra cserélhető. Kommutatív műveleteknél az operandusokat rendezzük, így `a+b` és `b+a` ugyanaz. Az *inlining* a hívást a függvény törzsével helyettesíti: megspórolja a hívás költségét, de legfőképp további optimalizációkat nyit meg (konstans-propagáció a hívó argumentumaival). Ára a kódméret-növekedés és az utasítás-cache romlása, ezért a fordítók költségmodell alapján, főleg kis és forró függvényeket inline-olnak.

```python
import itertools

def local_value_numbering(block):
    """CSE egy alapblokkon belül. Utasítás: (cél, op, a, b)."""
    value_of, table, holder, out = {}, {}, {}, []
    numbers = itertools.count()                    # egyedi értékszámok
    def vn(x):                                     # operandus értékszáma
        if isinstance(x, str) and x in value_of: return value_of[x]
        key = ("var", x) if isinstance(x, str) else ("const", x)
        if key not in table: table[key] = next(numbers)
        return table[key]
    for dst, op, a, b in block:
        ka, kb = vn(a), vn(b)
        if op in ("add", "mul"): ka, kb = sorted((ka, kb))   # kommutativitás
        key = (op, ka, kb)
        prev = holder.get(table.get(key))
        if prev is not None and value_of.get(prev) == table[key]:  # a tartó még érvényes?
            out.append((dst, "copy", prev, None))
            value_of[dst] = table[key]
        else:
            value_of[dst] = table[key] = next(numbers)   # új (vagy újraszámolt) érték
            holder[value_of[dst]] = dst
            out.append((dst, op, a, b))
    return out

block = [("t1", "add", "a", "b"),
         ("t2", "add", "b", "a"),    # -> copy t1 (kommutatív)
         ("a",  "mul", "t1", 2),
         ("t3", "add", "a", "b"),    # NEM azonos: 'a' közben megváltozott
         ("t4", "mul", "t1", 2)]     # -> copy a
for ins in local_value_numbering(block):
    print(ins)
```

```c
/* Inlining hatása: a hívás eltűnik, és a konstans argumentum miatt minden összeomlik. */
static inline int scale(int x, int factor) { return factor == 0 ? 0 : x * factor; }

int area(int w) {
    return scale(w, 4);          /* eredeti kód */
}
/* inlining után:            return 4 == 0 ? 0 : w * 4;
   konstans hajtogatás után: return w * 4;
   strength reduction után:  return w << 2;            */
```

## Regiszter-allokáció: linear scan
<!-- q: Hogyan osztja ki a fordító a változókat a CPU regisztereire? -->
<!-- tags: register allocation, linear scan, graph coloring, live intervals, spilling, code generation -->

A CPU-nak kevés regisztere van, a programnak sok változója: a regiszter-allokátor eldönti, melyik érték melyik regiszterben él, és melyik kerül a memóriába (*spill*). A gráfszínezéses módszer (Chaitin) interferenciagráfot épít az egyszerre élő változókból, és k színnel színezi — jó kódot ad, de lassú. A *linear scan* (JIT-ek kedvence, pl. HotSpot C1, V8) a változók élettartam-intervallumain egyszer halad végig; ha elfogy a regiszter, a legkésőbb lejáró intervallumot spilleli. Valóságban még hívási konvenciók, caller/callee-saved regiszterek és intervallum-szétvágás is bonyolítja.

```python
def live_intervals(code):
    """Élettartam: az első definíciótól az utolsó olvasásig (lineáris utasítássorrendben)."""
    start, end = {}, {}
    for i, (dst, srcs) in enumerate(code):
        for v in srcs:
            end[v] = i
        if dst:
            start.setdefault(dst, i)
            end[dst] = max(end.get(dst, i), i)
    return sorted((start[v], end[v], v) for v in start)

def linear_scan(intervals, registers):
    free, active = list(registers), []             # active: (vég, változó), vég szerint rendezve
    assignment, spilled = {}, set()
    for start, end, var in intervals:
        # 1) A már lejárt intervallumok regisztereit felszabadítjuk
        for e, v in list(active):
            if e <= start:                         # olvasás a definíció előtt történik
                active.remove((e, v))
                free.append(assignment[v])
        if free:
            assignment[var] = free.pop()
            active.append((end, var)); active.sort()
            continue
        # 2) Nincs szabad regiszter: a legkésőbb lejárót spilleljük (Poletto–Sarkar heurisztika)
        last_end, last_var = active[-1]
        if last_end > end:
            assignment[var] = assignment.pop(last_var)
            spilled.add(last_var)                  # ő a stackre (memóriába) költözik
            active[-1] = (end, var); active.sort()
        else:
            spilled.add(var)
    return assignment, spilled

code = [                     # (cél, olvasott változók)
    ("a", []), ("b", []), ("c", ["a", "b"]), ("d", ["a"]),
    ("e", ["c", "d"]), ("f", ["b", "e"]), (None, ["f"]),
]
iv = live_intervals(code)
print(iv)                    # [(0, 3, 'a'), (1, 5, 'b'), (2, 4, 'c'), ...]
alloc, spills = linear_scan(iv, ["r1", "r2"])
print("regiszterek:", alloc, "spill:", spills)
```

## JIT fordítás és tracing JIT
<!-- q: Hogyan működik a JIT fordító és a tracing JIT? -->
<!-- tags: jit, just in time, tracing jit, hot loop, guards, side exit, deoptimization, tiered compilation -->

A JIT futás közben fordít natív kódra: az interpreter számlálókkal méri, melyik kód „forró”, és csak azt fordítja (többszintű végrehajtás: interpreter → gyors JIT → optimalizáló JIT, pl. V8 Ignition/TurboFan, HotSpot C1/C2). A *tracing JIT* (LuaJIT, PyPy) nem függvényeket, hanem egy forró ciklus ténylegesen bejárt útvonalát (*trace*) rögzíti, az elágazásokat pedig *guard*-okká alakítja: ha a feltétel később másképp alakul, egy *side exit* visszaadja a vezérlést az interpreternek. A spekuláció (típusok, ágak) a gyorsaság forrása, a deoptimalizáció a biztonsági háló. Az alábbi szimulációban a „natív kód” egy generált, `exec`-kel lefordított Python függvény.

```python
import operator
OPS = {"add": operator.add, "lt": operator.lt, "mod": operator.mod}
SYM = {"add": "+", "lt": "<", "mod": "%"}
HOT = 4                                    # ennyi visszaugrás után kezdünk rögzíteni

PROG = [("set", "i", 0), ("set", "acc", 0),
        ("lt", "c", "i", 1000),            # 2: ciklusfej
        ("jif", "c", 9),                   # 3: ha c hamis -> kilépés
        ("mod", "m", "i", 3),
        ("jif", "m", 7),                   # 5: minden 3. i-nél kihagyja az összeadást
        ("add", "acc", "acc", "i"),
        ("add", "i", "i", 1),              # 7
        ("jmp", 2),                        # 8: visszaugrás -> forró ciklus jelölt
        ("halt",)]

def operand(x): return f"r[{x!r}]" if isinstance(x, str) else repr(x)

def compile_trace(ops):
    lines = ["def trace(r):", "    while True:"]
    for op in ops:
        if op[0] == "set": lines.append(f"        r[{op[1]!r}] = {op[2]!r}")
        elif op[0] in OPS:
            lines.append(f"        r[{op[1]!r}] = {operand(op[2])} {SYM[op[0]]} {operand(op[3])}")
        elif op[0] == "guard_true": lines.append(f"        if not r[{op[1]!r}]: return {op[2]}")
        elif op[0] == "guard_false": lines.append(f"        if r[{op[1]!r}]: return {op[2]}")
    ns = {}
    exec("\n".join(lines), ns)             # "JIT": forrás -> futtatható kód
    return ns["trace"], "\n".join(lines)

def run(prog):
    r, pc, counters, traces, rec, rec_start, exits = {}, 0, {}, {}, None, None, 0
    while True:
        if rec is None and pc in traces:
            pc = traces[pc](r); exits += 1     # trace fut, side exit-nél pc-t ad vissza
            continue
        op = prog[pc]
        if op[0] == "set": r[op[1]] = op[2]; pc += 1
        elif op[0] in OPS:
            r[op[1]] = OPS[op[0]](*(r[x] if isinstance(x, str) else x for x in op[2:])); pc += 1
        elif op[0] == "jif":
            taken = not r[op[1]]
            if rec is not None:                # a megfigyelt irányból guard lesz
                rec.append(("guard_false", op[1], pc + 1) if taken else ("guard_true", op[1], op[2]))
            pc = op[2] if taken else pc + 1
            continue
        elif op[0] == "jmp":
            target = pc = op[1]
            if rec is not None and target == rec_start:
                traces[target], src = compile_trace(rec); rec = None; print(src)
            elif rec is None and target not in traces:
                counters[target] = counters.get(target, 0) + 1
                if counters[target] >= HOT: rec, rec_start = [], target
            continue
        elif op[0] == "halt":
            return r, exits
        if rec is not None: rec.append(op)     # set/aritmetika bekerül a trace-be

regs, side_exits = run(PROG)
print("acc =", regs["acc"], "| side exitek száma:", side_exits)
```

## Szemétgyűjtés a runtime-ban: mark-sweep és társai
<!-- q: Hogyan működik a szemétgyűjtő (garbage collector) egy nyelvi runtime-ban? -->
<!-- tags: garbage collection, gc, mark and sweep, reference counting, generational gc, write barrier, roots -->

A tracing GC a *gyökerekből* (stack, globálisok, regiszterek) elérhető objektumokat megjelöli (mark), a többit felszabadítja (sweep); a ciklikus hivatkozásokat is kezeli, szemben a tiszta referenciaszámlálással. A *generációs* GC abból indul ki, hogy a legtöbb objektum fiatalon hal meg, ezért a fiatal generációt gyakran és olcsón (másolással) gyűjti, a régit ritkán; ehhez *write barrier* kell, ami nyilvántartja a régi → fiatal mutatókat. A küszöböt az élő halmazhoz igazítva amortizált költséget kapunk. A modern GC-k (G1, ZGC, Go) inkrementálisan/párhuzamosan dolgoznak a rövid szünetidőkért, tri-color jelöléssel.

```python
class Obj:
    __slots__ = ("name", "refs", "marked")
    def __init__(self, name):
        self.name, self.refs, self.marked = name, [], False

class Heap:
    def __init__(self, threshold=4):
        self.objects, self.roots, self.threshold = [], set(), threshold

    def alloc(self, name):
        if len(self.objects) >= self.threshold:          # allokációs nyomás indítja a GC-t
            self.collect()
            self.threshold = max(4, 2 * len(self.objects))  # küszöb az élő halmazhoz igazítva
        obj = Obj(name)
        self.objects.append(obj)
        return obj

    def collect(self):
        # MARK: explicit munkalista rekurzió helyett (mély láncnál sincs stack overflow)
        worklist = list(self.roots)
        while worklist:
            obj = worklist.pop()
            if not obj.marked:
                obj.marked = True
                worklist.extend(obj.refs)
        # SWEEP: jelöletlenek eldobása, a túlélők jelölésének törlése a következő körre
        dead = [o.name for o in self.objects if not o.marked]
        self.objects = [o for o in self.objects if o.marked]
        for o in self.objects:
            o.marked = False
        print(f"GC: felszabadítva {dead}, élő: {[o.name for o in self.objects]}")

heap = Heap()
root = heap.alloc("root"); heap.roots.add(root)
a, b = heap.alloc("a"), heap.alloc("b")
a.refs.append(b); b.refs.append(a)       # ciklus: refcount-tal sosem szabadulna fel
child = heap.alloc("child"); root.refs.append(child)
heap.alloc("tmp")                        # küszöb elérve -> GC: a, b felszabadul, root+child él
```

## LLVM IR alapjai
<!-- q: Hogyan néz ki az LLVM IR és hogyan használja egy fordító? -->
<!-- tags: llvm, llvm ir, ssa, phi, basic block, clang, opt, llc, backend -->

Az LLVM IR egy típusos, SSA alapú, assembly-szerű köztes nyelv: a frontend (Clang, rustc, Swift) ezt generálja, az `opt` optimalizálja, az `llc` pedig gépi kódra fordítja bármely támogatott architektúrára. Minden érték egyszer definiált (`%név`), az alapblokkok terminátorral (`br`, `ret`) zárulnak, a ciklusváltozók `phi`-vel kapnak értéket. Frontendet írni egyszerűbb, ha a változókat először `alloca` + `load`/`store` párossal kezeled, és a `mem2reg` passzra bízod az SSA-ra alakítást. Az `nsw` (no signed wrap) flag ígéret: túlcsordulás esetén az eredmény poison, ami további optimalizációt enged.

```llvm
; Faktoriális ciklussal, SSA formában (nagyjából így néz ki clang -O1 után)
define i64 @fact(i64 %n) {
entry:
  %small = icmp sle i64 %n, 1                  ; n <= 1 ?
  br i1 %small, label %done, label %loop

loop:                                          ; ciklustörzs = egyetlen alapblokk
  %i   = phi i64 [ %n, %entry ], [ %i.next, %loop ]
  %acc = phi i64 [ 1, %entry ],  [ %acc.next, %loop ]
  %acc.next = mul nsw i64 %acc, %i             ; acc *= i
  %i.next   = sub nsw i64 %i, 1                ; i -= 1
  %again    = icmp sgt i64 %i.next, 1
  br i1 %again, label %loop, label %done

done:                                          ; phi: honnan érkeztünk?
  %res = phi i64 [ 1, %entry ], [ %acc.next, %loop ]
  ret i64 %res
}

; Frontend-barát alak mem2reg előtt: a változó egy stack-slot
define i32 @inc(i32 %x) {
entry:
  %x.addr = alloca i32
  store i32 %x, ptr %x.addr
  %v = load i32, ptr %x.addr
  %r = add i32 %v, 1
  ret i32 %r
}
```

```bash
# C -> IR -> optimalizált IR -> assembly
clang -O0 -Xclang -disable-O0-optnone -S -emit-llvm fact.c -o fact.ll
opt -passes=mem2reg,instcombine,simplifycfg -S fact.ll -o fact.opt.ll
llc -O2 fact.opt.ll -o fact.s
```

## Parser generátorok: Lark, ANTLR, yacc
<!-- q: Mikor használjak parser generátort kézzel írt parser helyett? -->
<!-- tags: parser generator, lark, antlr, yacc, bison, lalr, peg, grammar -->

A parser generátor a nyelvtanból automatikusan állít elő parsert: a yacc/bison és a Lark `lalr` módja LALR(1) táblákat épít (gyors, balrekurziót kezel, de a konfliktusüzenetek nehezen érthetők), az ANTLR ALL(*) algoritmust használ és sok célnyelvre generál, a PEG-alapúak (pest, PEG.js, CPython 3.9+ parsere) rendezett választással dolgoznak. Akkor éri meg, ha a nyelvtan gyakran változik, vagy gyorsan kell egy DSL/konfignyelv; kézzel írt parser akkor jobb, ha kiváló hibaüzenet, hibatűrés (IDE) vagy maximális sebesség kell. A Larkban a `->` alias nevezi el a fa csomópontját, a `?` pedig kilapítja az egygyerekes szabályokat.

```python
from lark import Lark, Transformer, v_args

GRAMMAR = r"""
    ?start: expr
    ?expr: expr "+" term   -> add
         | expr "-" term   -> sub
         | term
    ?term: term "*" factor -> mul
         | term "/" factor -> div
         | factor
    ?factor: NUMBER        -> number
           | "-" factor    -> neg
           | NAME          -> var
           | "(" expr ")"
    %import common.CNAME -> NAME
    %import common.NUMBER
    %import common.WS
    %ignore WS
"""

@v_args(inline=True)                 # a gyerekeket külön argumentumként kapjuk
class Evaluate(Transformer):
    def __init__(self, env):
        super().__init__()
        self.env = env
    def number(self, tok): return float(tok)
    def var(self, name):
        if str(name) not in self.env: raise NameError(f"ismeretlen: {name}")
        return self.env[str(name)]
    def add(self, a, b): return a + b
    def sub(self, a, b): return a - b
    def mul(self, a, b): return a * b
    def div(self, a, b): return a / b
    def neg(self, a): return -a

parser = Lark(GRAMMAR, parser="lalr")   # LALR(1): balrekurzív szabályok is működnek
tree = parser.parse("2 * (x + 3) - -1")
print(tree.pretty())
print(Evaluate({"x": 4}).transform(tree))   # 15.0
```

```antlr
// Ugyanez ANTLR4-ben: a precedenciát az alternatívák sorrendje adja
grammar Expr;
expr : expr ('*' | '/') expr   # MulDiv
     | expr ('+' | '-') expr   # AddSub
     | '-' expr                # Neg
     | NUMBER                  # Num
     | NAME                    # Var
     | '(' expr ')'            # Parens
     ;
NUMBER : [0-9]+ ('.' [0-9]+)? ;
NAME   : [a-zA-Z_] [a-zA-Z_0-9]* ;
WS     : [ \t\r\n]+ -> skip ;
```
