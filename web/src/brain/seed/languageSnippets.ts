// languageSnippets.ts — short, original, WORKING code examples for every language
// of the programming-languages pack (see languages.ts), from the very basics
// (hello world, variables, if, loops, functions) up to each ecosystem's essentials.
// Appended to PROGRAMMING_SNIPPETS: findSnippet() answers "how to …" questions with
// them, and the 3D brain shows each one as a 'doc' neuron on its tech hub.
//
// `alt` = extra accent-free Hungarian word STEMS that also match ("ciklus" hits
// "ciklust", "ciklussal"), so Hungarian questions find the right example too.
import type { ProgSnippet } from './programmingCurated';

const r = String.raw; // keep backslashes literal (printf("…\n"), C:\path, Swift "\(x)")

const PY = 'https://docs.python.org/3/tutorial/';
const MDN_JS = 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/';
const MDN = 'https://developer.mozilla.org/en-US/docs/Web/';
const TS = 'https://www.typescriptlang.org/docs/handbook/';
const JAVA = 'https://dev.java/learn/';
const CREF = 'https://en.cppreference.com/w/';
const CS = 'https://learn.microsoft.com/en-us/dotnet/csharp/';
const DOTNET = 'https://learn.microsoft.com/en-us/dotnet/';
const MUI = 'https://mui.com/material-ui/';
const BASH = 'https://www.gnu.org/software/bash/manual/bash.html';
const MAN = 'https://man7.org/linux/man-pages/';
const WIN = 'https://learn.microsoft.com/en-us/';
const SWIFT = 'https://docs.swift.org/swift-book/documentation/the-swift-programming-language/';
const GO = 'https://go.dev/';
const RUST = 'https://doc.rust-lang.org/book/';
const KT = 'https://kotlinlang.org/docs/';
const PHP = 'https://www.php.net/manual/en/';
const MYSQL = 'https://dev.mysql.com/doc/refman/8.0/en/';

export const LANG_SNIPPETS: ProgSnippet[] = [
  // ── Python ───────────────────────────────────────────────────────────────────
  { tech: 'python', title: 'Hello world in Python', alt: ['kiir'], code: r`print("Hello, World!")`, source: `${PY}introduction.html` },
  { tech: 'python', title: 'Variables and types in Python', alt: ['valtozo', 'tipus'], code: r`name = "Auri"      # str
age = 3            # int
pi = 3.14          # float
active = True      # bool
print(type(age))   # <class 'int'>`, source: `${PY}introduction.html` },
  { tech: 'python', title: 'If elif else in Python', alt: ['feltetel', 'elagazas'], code: r`score = 72
if score >= 90:
    print("excellent")
elif score >= 50:
    print("passed")
else:
    print("failed")`, source: `${PY}controlflow.html#if-statements` },
  { tech: 'python', title: 'While loop in Python', alt: ['ciklus'], code: r`n = 3
while n > 0:
    print(n)
    n -= 1`, source: `${PY}introduction.html#first-steps-towards-programming` },
  { tech: 'python', title: 'Read user input in Python', alt: ['beolvas', 'beker'], code: r`name = input("Your name: ")
age = int(input("Your age: "))
print(f"Hi {name}, next year you will be {age + 1}.")`, source: 'https://docs.python.org/3/library/functions.html#input' },
  { tech: 'python', title: 'Dictionary in Python (dict)', alt: ['szotar'], code: r`user = {"name": "Ann", "age": 30}
user["email"] = "ann@example.com"
for key, value in user.items():
    print(key, value)
print(user.get("phone", "none"))`, source: `${PY}datastructures.html#dictionaries` },
  { tech: 'python', title: 'Try except error handling in Python', alt: ['hibakezel', 'kivetel'], code: r`try:
    n = int("abc")
except ValueError as e:
    print("Not a number:", e)
finally:
    print("done")`, source: `${PY}errors.html` },
  { tech: 'python', title: 'Write a file in Python', alt: ['fajl', 'iras'], code: r`with open("out.txt", "w", encoding="utf-8") as f:
    f.write("Hello\n")`, source: `${PY}inputoutput.html#reading-and-writing-files` },
  { tech: 'python', title: 'Virtual environment in Python (venv and pip)', alt: ['virtualis', 'kornyezet', 'telepit'], code: r`python -m venv .venv
# Windows:      .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
pip install requests`, source: 'https://docs.python.org/3/library/venv.html' },
  { tech: 'python', title: 'Main guard in Python (__main__)', code: r`def main():
    print("running")

if __name__ == "__main__":
    main()`, source: 'https://docs.python.org/3/library/__main__.html' },
  { tech: 'python', title: 'Sort a list in Python', alt: ['rendez', 'lista'], code: r`nums = [3, 1, 2]
nums.sort()                               # in place: [1, 2, 3]
words = sorted(["b", "A", "c"], key=str.lower)
top = sorted(nums, reverse=True)`, source: 'https://docs.python.org/3/howto/sorting.html' },

  // ── JavaScript ───────────────────────────────────────────────────────────────
  { tech: 'javascript', title: 'Hello world in JavaScript', alt: ['kiir'], code: r`console.log("Hello, World!");`, source: `${MDN}API/console` },
  { tech: 'javascript', title: 'Variables in JavaScript (let and const)', alt: ['valtozo'], code: r`const name = "Auri";   // cannot be reassigned
let count = 0;         // can change
count += 1;`, source: `${MDN_JS}Reference/Statements/let` },
  { tech: 'javascript', title: 'If else in JavaScript', alt: ['feltetel', 'elagazas'], code: r`if (age >= 18) {
  console.log("adult");
} else if (age >= 14) {
  console.log("teen");
} else {
  console.log("child");
}`, source: `${MDN_JS}Reference/Statements/if...else` },
  { tech: 'javascript', title: 'For loop in JavaScript', alt: ['ciklus'], code: r`for (let i = 0; i < 5; i++) {
  console.log(i);
}`, source: `${MDN_JS}Reference/Statements/for` },
  { tech: 'javascript', title: 'Function and arrow function in JavaScript', alt: ['fuggveny'], code: r`function add(a, b) {
  return a + b;
}
const multiply = (a, b) => a * b;`, source: `${MDN_JS}Guide/Functions` },
  { tech: 'javascript', title: 'Object in JavaScript', alt: ['objektum'], code: r`const user = { name: "Ann", age: 30 };
user.email = "ann@example.com";
console.log(Object.keys(user)); // ["name", "age", "email"]`, source: `${MDN_JS}Guide/Working_with_objects` },
  { tech: 'javascript', title: 'Class in JavaScript', alt: ['osztaly'], code: 'class Animal {\n  constructor(name) {\n    this.name = name;\n  }\n  speak() {\n    return `${this.name} makes a sound`;\n  }\n}\nconst rex = new Animal("Rex");', source: `${MDN_JS}Reference/Classes` },
  { tech: 'javascript', title: 'Try catch with async await in JavaScript', alt: ['hibakezel'], code: r`async function load(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("HTTP " + res.status);
    return await res.json();
  } catch (err) {
    console.error("Failed:", err);
  }
}`, source: `${MDN_JS}Reference/Statements/async_function` },
  { tech: 'javascript', title: 'Click event in JavaScript (addEventListener)', alt: ['kattint', 'gomb'], code: r`const btn = document.querySelector("#save");
btn.addEventListener("click", () => {
  alert("Saved!");
});`, source: `${MDN}API/EventTarget/addEventListener` },
  { tech: 'javascript', title: 'Template literal string in JavaScript', alt: ['szoveg'], code: 'const msg = `Hello, ${name}! You have ${count} new messages.`;', source: `${MDN_JS}Reference/Template_literals` },
  { tech: 'javascript', title: 'setTimeout and setInterval timer in JavaScript', alt: ['idozit'], code: r`setTimeout(() => console.log("after 1 second"), 1000);
const id = setInterval(() => console.log("tick"), 500);
clearInterval(id); // stop it`, source: `${MDN}API/Window/setTimeout` },

  // ── TypeScript ───────────────────────────────────────────────────────────────
  { tech: 'typescript', title: 'Hello world in TypeScript', alt: ['kiir'], code: r`const greeting: string = "Hello, World!";
console.log(greeting);`, source: `${TS}intro.html` },
  { tech: 'typescript', title: 'Basic types in TypeScript', alt: ['tipus', 'valtozo'], code: r`let age: number = 30;
let name: string = "Ann";
let done: boolean = false;
let tags: string[] = ["a", "b"];
let point: [number, number] = [3, 4]; // tuple`, source: `${TS}2/everyday-types.html` },
  { tech: 'typescript', title: 'Interface in TypeScript', alt: ['interfesz'], code: r`interface User {
  id: number;
  name: string;
  email?: string; // optional
}
const u: User = { id: 1, name: "Ann" };`, source: `${TS}2/objects.html` },
  { tech: 'typescript', title: 'Typed function in TypeScript', alt: ['fuggveny'], code: r`function add(a: number, b: number): number {
  return a + b;
}
const greet = (name: string): string => "Hi " + name;`, source: `${TS}2/functions.html` },
  { tech: 'typescript', title: 'Union type in TypeScript', alt: ['tipus'], code: r`type Status = "idle" | "loading" | "error";
let s: Status = "idle";
function show(id: number | string) {
  console.log(typeof id === "number" ? id.toFixed(0) : id.toUpperCase());
}`, source: `${TS}2/everyday-types.html#union-types` },
  { tech: 'typescript', title: 'Generic function in TypeScript', alt: ['generikus'], code: r`function first<T>(items: T[]): T | undefined {
  return items[0];
}
const n = first([1, 2, 3]); // number | undefined`, source: `${TS}2/generics.html` },
  { tech: 'typescript', title: 'Compile TypeScript with tsc', alt: ['fordit', 'telepit'], code: r`npm install -D typescript
npx tsc --init   # creates tsconfig.json
npx tsc          # compiles .ts files to .js`, source: `${TS}compiler-options.html` },
  { tech: 'typescript', title: 'Enum in TypeScript', code: r`enum Direction { Up, Down, Left, Right }
const d: Direction = Direction.Up;`, source: `${TS}enums.html` },

  // ── HTML ─────────────────────────────────────────────────────────────────────
  { tech: 'html', title: 'HTML5 page boilerplate (basic structure)', alt: ['alap', 'szerkezet', 'sablon'], code: r`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>My page</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <h1>Hello, World!</h1>
  <script src="app.js"></script>
</body>
</html>`, source: `${MDN}HTML/Element/html` },
  { tech: 'html', title: 'Headings and paragraphs in HTML', alt: ['cimsor', 'bekezdes'], code: r`<h1>Main title</h1>
<h2>Subtitle</h2>
<p>A paragraph with <strong>bold</strong> and <em>italic</em> text.</p>`, source: `${MDN}HTML/Element/Heading_Elements` },
  { tech: 'html', title: 'Lists in HTML (ul and ol)', alt: ['lista'], code: r`<ul>
  <li>Apple</li>
  <li>Pear</li>
</ul>
<ol>
  <li>First step</li>
  <li>Second step</li>
</ol>`, source: `${MDN}HTML/Element/ul` },
  { tech: 'html', title: 'Table in HTML', alt: ['tablazat'], code: r`<table>
  <thead>
    <tr><th>Name</th><th>Age</th></tr>
  </thead>
  <tbody>
    <tr><td>Ann</td><td>30</td></tr>
  </tbody>
</table>`, source: `${MDN}HTML/Element/table` },
  { tech: 'html', title: 'Semantic layout in HTML', alt: ['szemantik'], code: r`<header><nav>…</nav></header>
<main>
  <section><h2>About</h2></section>
  <article>…</article>
</main>
<footer>© 2026</footer>`, source: `${MDN}HTML/Element/main` },
  { tech: 'html', title: 'Button with a script in HTML', alt: ['gomb'], code: r`<button id="hi">Say hi</button>
<script>
  document.getElementById("hi").onclick = () => alert("Hi!");
</script>`, source: `${MDN}HTML/Element/button` },
  { tech: 'html', title: 'Video and audio in HTML', alt: ['video', 'hang'], code: r`<video src="clip.mp4" controls width="480"></video>
<audio src="song.mp3" controls></audio>`, source: `${MDN}HTML/Element/video` },

  // ── CSS ──────────────────────────────────────────────────────────────────────
  { tech: 'css', title: 'CSS selectors basics', alt: ['szelektor'], code: r`p { color: #333; }           /* every <p> */
.card { padding: 16px; }     /* class="card" */
#logo { width: 120px; }      /* id="logo" */
nav a:hover { color: red; }  /* links in nav, on hover */`, source: `${MDN}CSS/CSS_selectors` },
  { tech: 'css', title: 'Box model in CSS (margin padding border)', alt: ['doboz'], code: r`.box {
  margin: 16px;            /* outside */
  padding: 12px;           /* inside */
  border: 2px solid #444;
  box-sizing: border-box;  /* width includes padding + border */
}`, source: `${MDN}CSS/CSS_box_model` },
  { tech: 'css', title: 'Colors and fonts in CSS', alt: ['szin', 'betu'], code: r`body {
  font-family: system-ui, sans-serif;
  font-size: 16px;
  color: #222;
  background: #f5f5f5;
}`, source: `${MDN}CSS/font-family` },
  { tech: 'css', title: 'Media query in CSS (responsive)', alt: ['reszponziv', 'mobil'], code: r`.grid { display: grid; grid-template-columns: repeat(3, 1fr); }
@media (max-width: 600px) {
  .grid { grid-template-columns: 1fr; }
}`, source: `${MDN}CSS/CSS_media_queries/Using_media_queries` },
  { tech: 'css', title: 'Hover transition in CSS', alt: ['animacio', 'atmenet'], code: r`.btn { background: #0af; transition: background 0.2s ease; }
.btn:hover { background: #08c; }`, source: `${MDN}CSS/transition` },
  { tech: 'css', title: 'CSS variables (custom properties)', alt: ['valtozo'], code: r`:root { --primary: #0af; --gap: 12px; }
.btn { background: var(--primary); margin: var(--gap); }`, source: `${MDN}CSS/Using_CSS_custom_properties` },
  { tech: 'css', title: 'Dark mode in CSS', alt: ['sotet'], code: r`@media (prefers-color-scheme: dark) {
  body { background: #111; color: #eee; }
}`, source: `${MDN}CSS/@media/prefers-color-scheme` },

  // ── Java ─────────────────────────────────────────────────────────────────────
  { tech: 'java', title: 'Variables and types in Java', alt: ['valtozo', 'tipus'], code: r`int age = 30;
double price = 9.99;
boolean active = true;
char grade = 'A';
String name = "Ann";
var count = 10; // type inferred (int)`, source: `${JAVA}language-basics/variables/` },
  { tech: 'java', title: 'If else in Java', alt: ['feltetel', 'elagazas'], code: r`if (score >= 50) {
    System.out.println("passed");
} else {
    System.out.println("failed");
}`, source: `${JAVA}language-basics/controlling-flow/` },
  { tech: 'java', title: 'While loop in Java', alt: ['ciklus'], code: r`int n = 3;
while (n > 0) {
    System.out.println(n);
    n--;
}`, source: `${JAVA}language-basics/controlling-flow/` },
  { tech: 'java', title: 'Method in Java (static function)', alt: ['fuggveny', 'metodus'], code: r`static int add(int a, int b) {
    return a + b;
}`, source: `${JAVA}classes-objects/defining-methods/` },
  { tech: 'java', title: 'Read user input in Java (Scanner)', alt: ['beolvas', 'beker'], code: r`import java.util.Scanner;

Scanner sc = new Scanner(System.in);
System.out.print("Name: ");
String name = sc.nextLine();
int age = sc.nextInt();`, source: 'https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Scanner.html' },
  { tech: 'java', title: 'HashMap in Java', alt: ['szotar'], code: r`Map<String, Integer> ages = new HashMap<>();
ages.put("Ann", 30);
int a = ages.getOrDefault("Ann", 0);
for (var e : ages.entrySet()) {
    System.out.println(e.getKey() + "=" + e.getValue());
}`, source: `${JAVA}api/collections-framework/` },
  { tech: 'java', title: 'Try catch exception in Java', alt: ['hibakezel', 'kivetel'], code: r`try {
    int n = Integer.parseInt("abc");
} catch (NumberFormatException e) {
    System.out.println("Not a number: " + e.getMessage());
} finally {
    System.out.println("done");
}`, source: `${JAVA}exceptions/` },
  { tech: 'java', title: 'Interface in Java', alt: ['interfesz'], code: r`interface Shape {
    double area();
}
class Circle implements Shape {
    private final double r;
    Circle(double r) { this.r = r; }
    public double area() { return Math.PI * r * r; }
}`, source: `${JAVA}interfaces/` },
  { tech: 'java', title: 'Record in Java', code: r`record User(String name, int age) {}

User u = new User("Ann", 30);
System.out.println(u.name());`, source: `${JAVA}records/` },
  { tech: 'java', title: 'Stream filter map in Java', alt: ['szur'], code: r`List<Integer> evens = nums.stream()
    .filter(n -> n % 2 == 0)
    .map(n -> n * 10)
    .toList();`, source: `${JAVA}api/streams/` },

  // ── C ────────────────────────────────────────────────────────────────────────
  { tech: 'c', title: 'Hello world in C', alt: ['kiir'], code: r`#include <stdio.h>

int main(void) {
    printf("Hello, World!\n");
    return 0;
}`, source: `${CREF}c/io/fprintf` },
  { tech: 'c', title: 'Variables and types in C', alt: ['valtozo', 'tipus'], code: r`int age = 30;
float price = 9.99f;
double pi = 3.14159;
char grade = 'A';
printf("%d %.2f %c\n", age, price, grade);`, source: `${CREF}c/language/arithmetic_types` },
  { tech: 'c', title: 'If else in C', alt: ['feltetel', 'elagazas'], code: r`if (x > 0) {
    printf("positive\n");
} else if (x < 0) {
    printf("negative\n");
} else {
    printf("zero\n");
}`, source: `${CREF}c/language/if` },
  { tech: 'c', title: 'For loop in C', alt: ['ciklus'], code: r`for (int i = 0; i < 10; i++) {
    printf("%d\n", i);
}`, source: `${CREF}c/language/for` },
  { tech: 'c', title: 'Function in C', alt: ['fuggveny'], code: r`#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int main(void) {
    printf("%d\n", add(2, 3));
    return 0;
}`, source: `${CREF}c/language/functions` },
  { tech: 'c', title: 'Array in C', alt: ['tomb'], code: r`int nums[5] = {1, 2, 3, 4, 5};
int sum = 0;
for (int i = 0; i < 5; i++) {
    sum += nums[i];
}`, source: `${CREF}c/language/array` },
  { tech: 'c', title: 'Pointer in C', alt: ['mutato', 'memoria'], code: r`int x = 42;
int *p = &x;        // p holds the address of x
*p = 7;             // change x through the pointer
printf("%d\n", x);  // 7`, source: `${CREF}c/language/pointer` },
  { tech: 'c', title: 'Struct in C', alt: ['struktura'], code: r`struct Point {
    int x;
    int y;
};

struct Point p = {3, 4};
printf("%d,%d\n", p.x, p.y);`, source: `${CREF}c/language/struct` },
  { tech: 'c', title: 'Malloc and free in C (dynamic memory)', alt: ['memoria', 'foglal'], code: r`#include <stdlib.h>

int *arr = malloc(10 * sizeof(int));
if (arr == NULL) return 1;   // always check
arr[0] = 5;
free(arr);                   // give it back`, source: `${CREF}c/memory/malloc` },
  { tech: 'c', title: 'Read input in C (scanf)', alt: ['beolvas', 'beker'], code: r`int age;
printf("Age: ");
if (scanf("%d", &age) == 1) {
    printf("You are %d\n", age);
}`, source: `${CREF}c/io/fscanf` },
  { tech: 'c', title: 'Read a file in C', alt: ['fajl'], code: r`FILE *f = fopen("data.txt", "r");
if (f == NULL) return 1;
char line[256];
while (fgets(line, sizeof line, f)) {
    printf("%s", line);
}
fclose(f);`, source: `${CREF}c/io/fopen` },
  { tech: 'c', title: 'String in C (char array)', alt: ['szoveg'], code: r`#include <string.h>

char name[32];
snprintf(name, sizeof name, "%s", "Auri");
printf("%zu\n", strlen(name)); // 4`, source: `${CREF}c/string/byte/strlen` },
  { tech: 'c', title: 'Compile and run C with gcc', alt: ['fordit', 'futtat'], code: r`gcc main.c -o main -Wall
./main`, source: 'https://gcc.gnu.org/onlinedocs/gcc/Invoking-GCC.html' },

  // ── C++ ──────────────────────────────────────────────────────────────────────
  { tech: 'cpp', title: 'Hello world in C++', alt: ['kiir'], code: r`#include <iostream>

int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}`, source: `${CREF}cpp/io/cout` },
  { tech: 'cpp', title: 'Read input in C++ (cin)', alt: ['beolvas', 'beker'], code: r`#include <iostream>
#include <string>

std::string name;
int age;
std::cin >> name >> age;
std::cout << name << " is " << age << "\n";`, source: `${CREF}cpp/io/cin` },
  { tech: 'cpp', title: 'Vector in C++ (dynamic array)', alt: ['tomb', 'lista'], code: r`#include <vector>

std::vector<int> nums = {1, 2, 3};
nums.push_back(4);
for (int n : nums) {
    std::cout << n << " ";
}`, source: `${CREF}cpp/container/vector` },
  { tech: 'cpp', title: 'Class in C++', alt: ['osztaly'], code: r`class Rect {
public:
    Rect(double w, double h) : w_(w), h_(h) {}
    double area() const { return w_ * h_; }
private:
    double w_, h_;
};`, source: `${CREF}cpp/language/classes` },
  { tech: 'cpp', title: 'String in C++ (std::string)', alt: ['szoveg'], code: r`#include <string>

std::string s = "Hello";
s += ", World";
std::cout << s.size() << " " << s.substr(0, 5) << "\n";`, source: `${CREF}cpp/string/basic_string` },
  { tech: 'cpp', title: 'Map in C++ (std::map)', alt: ['szotar'], code: r`#include <map>

std::map<std::string, int> ages;
ages["Ann"] = 30;
for (const auto& [name, age] : ages) {
    std::cout << name << "=" << age << "\n";
}`, source: `${CREF}cpp/container/map` },
  { tech: 'cpp', title: 'Smart pointer in C++ (unique_ptr)', alt: ['mutato', 'memoria'], code: r`#include <memory>

auto r = std::make_unique<Rect>(2.0, 3.0);
std::cout << r->area() << "\n";   // freed automatically, no delete`, source: `${CREF}cpp/memory/unique_ptr` },
  { tech: 'cpp', title: 'Template function in C++', alt: ['sablon'], code: r`template <typename T>
T maxOf(T a, T b) {
    return a > b ? a : b;
}`, source: `${CREF}cpp/language/templates` },
  { tech: 'cpp', title: 'Sort with a lambda in C++', alt: ['rendez'], code: r`#include <algorithm>

std::sort(nums.begin(), nums.end(), [](int a, int b) { return a > b; });`, source: `${CREF}cpp/algorithm/sort` },
  { tech: 'cpp', title: 'Compile and run C++ with g++', alt: ['fordit', 'futtat'], code: r`g++ -std=c++20 -Wall main.cpp -o main
./main`, source: 'https://gcc.gnu.org/onlinedocs/gcc/Invoking-GCC.html' },

  // ── C# ───────────────────────────────────────────────────────────────────────
  { tech: 'csharp', title: 'Hello world in C#', alt: ['kiir'], code: r`// Program.cs — top-level statements
Console.WriteLine("Hello, World!");`, source: `${CS}tour-of-csharp/` },
  { tech: 'csharp', title: 'Variables and types in C#', alt: ['valtozo', 'tipus'], code: r`int age = 30;
double price = 9.99;
bool active = true;
string name = "Ann";
var count = 10; // inferred as int`, source: `${CS}fundamentals/types/` },
  { tech: 'csharp', title: 'If else in C#', alt: ['feltetel', 'elagazas'], code: r`if (score >= 50)
{
    Console.WriteLine("passed");
}
else
{
    Console.WriteLine("failed");
}`, source: `${CS}language-reference/statements/selection-statements` },
  { tech: 'csharp', title: 'For and foreach loop in C#', alt: ['ciklus'], code: r`for (int i = 0; i < 5; i++)
{
    Console.WriteLine(i);
}

foreach (var name in names)
{
    Console.WriteLine(name);
}`, source: `${CS}language-reference/statements/iteration-statements` },
  { tech: 'csharp', title: 'Method in C#', alt: ['fuggveny', 'metodus'], code: r`static int Add(int a, int b) => a + b;

static string Greet(string name = "World")
{
    return $"Hello, {name}!";
}`, source: `${CS}methods` },
  { tech: 'csharp', title: 'Class and properties in C#', alt: ['osztaly'], code: r`public class User
{
    public string Name { get; set; } = "";
    public int Age { get; set; }
    public string Greet() => $"Hi, I am {Name}";
}

var u = new User { Name = "Ann", Age = 30 };`, source: `${CS}fundamentals/types/classes` },
  { tech: 'csharp', title: 'List in C#', alt: ['lista', 'tomb'], code: r`var names = new List<string> { "Ann", "Bob" };
names.Add("Cecil");
Console.WriteLine(names.Count); // 3`, source: 'https://learn.microsoft.com/en-us/dotnet/api/system.collections.generic.list-1' },
  { tech: 'csharp', title: 'LINQ query in C#', alt: ['lekerdez', 'szur'], code: r`var adults = people
    .Where(p => p.Age >= 18)
    .OrderBy(p => p.Name)
    .Select(p => p.Name)
    .ToList();`, source: `${CS}linq/` },
  { tech: 'csharp', title: 'Try catch exception in C#', alt: ['hibakezel', 'kivetel'], code: r`try
{
    int n = int.Parse("abc");
}
catch (FormatException ex)
{
    Console.WriteLine($"Not a number: {ex.Message}");
}`, source: `${CS}fundamentals/exceptions/` },
  { tech: 'csharp', title: 'Async await HTTP call in C#', alt: ['aszinkron'], code: r`using var http = new HttpClient();
string html = await http.GetStringAsync("https://example.com");
Console.WriteLine(html.Length);`, source: `${CS}asynchronous-programming/` },
  { tech: 'csharp', title: 'Record in C#', code: r`public record Point(int X, int Y);

var p = new Point(1, 2);
var q = p with { X = 5 };   // copy with a change`, source: `${CS}language-reference/builtin-types/record` },
  { tech: 'csharp', title: 'Read user input in C#', alt: ['beolvas', 'beker'], code: r`Console.Write("Name: ");
string? name = Console.ReadLine();
if (int.TryParse(Console.ReadLine(), out int age))
{
    Console.WriteLine($"{name} is {age}");
}`, source: 'https://learn.microsoft.com/en-us/dotnet/api/system.console.readline' },
  { tech: 'csharp', title: 'C# 14 new features in .NET 10 (field keyword, extension members)', alt: ['ujdonsag'], code: r`// 'field' = the property's compiler-generated backing field
public string Name
{
    get;
    set => field = value?.Trim() ?? "";
}

// extension members: extension properties, not only methods
public static class StringExtensions
{
    extension(string s)
    {
        public bool IsBlank => string.IsNullOrWhiteSpace(s);
    }
}
// "  ".IsBlank == true`, source: `${CS}whats-new/csharp-14` },

  // ── .NET 10 ──────────────────────────────────────────────────────────────────
  { tech: 'dotnet', title: 'Create a console app with the dotnet CLI (.NET 10)', alt: ['projekt', 'letrehoz'], code: r`dotnet new console -n HelloApp
cd HelloApp
dotnet run`, source: `${DOTNET}core/tools/dotnet-new` },
  { tech: 'dotnet', title: 'Run a single C# file with .NET 10 (dotnet run app.cs)', alt: ['futtat'], code: r`// hello.cs
Console.WriteLine($"Hello from .NET {Environment.Version}");

// terminal (no .csproj needed since .NET 10):
// dotnet run hello.cs`, source: `${DOTNET}core/whats-new/dotnet-10/sdk` },
  { tech: 'dotnet', title: 'Minimal API web server in ASP.NET Core (.NET 10)', alt: ['szerver', 'webapi'], code: r`var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/", () => "Hello from .NET 10!");
app.MapGet("/users/{id:int}", (int id) => new { Id = id, Name = "Ann" });

app.Run();`, source: 'https://learn.microsoft.com/en-us/aspnet/core/fundamentals/minimal-apis' },
  { tech: 'dotnet', title: 'Add a NuGet package in .NET', alt: ['csomag', 'telepit'], code: r`dotnet add package Microsoft.EntityFrameworkCore.Sqlite
dotnet restore
dotnet build`, source: `${DOTNET}core/tools/` },
  { tech: 'dotnet', title: 'Project templates in .NET (webapi, wpf, maui)', alt: ['sablon', 'projekt'], code: r`dotnet new list                 # every template
dotnet new webapi -n MyApi
dotnet new wpf -n MyDesktopApp
dotnet new maui -n MyMobileApp`, source: `${DOTNET}core/tools/dotnet-new` },
  { tech: 'dotnet', title: 'Check the .NET version and SDKs', alt: ['verzio'], code: r`dotnet --version
dotnet --list-sdks
dotnet --info`, source: `${DOTNET}core/tools/` },
  { tech: 'dotnet', title: 'Entity Framework Core DbContext in .NET', alt: ['adatbazis'], code: r`public class AppDb(DbContextOptions<AppDb> options) : DbContext(options)
{
    public DbSet<User> Users => Set<User>();
}

// dotnet ef migrations add Init
// dotnet ef database update`, source: 'https://learn.microsoft.com/en-us/ef/core/' },

  // ── WPF ──────────────────────────────────────────────────────────────────────
  { tech: 'wpf', title: 'WPF window in XAML', alt: ['ablak', 'felulet'], code: r`<Window x:Class="Demo.MainWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Demo" Height="200" Width="320">
  <StackPanel Margin="12">
    <TextBox x:Name="NameBox" />
    <Button Content="Greet" Click="Greet_Click" Margin="0,8,0,0" />
  </StackPanel>
</Window>`, source: `${DOTNET}desktop/wpf/` },
  { tech: 'wpf', title: 'WPF button click handler (code-behind)', alt: ['gomb', 'kattint'], code: r`private void Greet_Click(object sender, RoutedEventArgs e)
{
    MessageBox.Show($"Hello, {NameBox.Text}!");
}`, source: `${DOTNET}desktop/wpf/events/` },
  { tech: 'wpf', title: 'WPF data binding with MVVM', alt: ['adatkot'], code: r`public class MainViewModel : INotifyPropertyChanged
{
    private string _name = "";
    public string Name
    {
        get => _name;
        set { _name = value; PropertyChanged?.Invoke(this, new(nameof(Name))); }
    }
    public event PropertyChangedEventHandler? PropertyChanged;
}

// XAML: <TextBox Text="{Binding Name, UpdateSourceTrigger=PropertyChanged}" />`, source: `${DOTNET}desktop/wpf/data/` },
  { tech: 'wpf', title: 'WPF Grid layout', alt: ['elrendez'], code: r`<Grid>
  <Grid.ColumnDefinitions>
    <ColumnDefinition Width="Auto" />
    <ColumnDefinition Width="*" />
  </Grid.ColumnDefinitions>
  <Label Content="Name:" Grid.Column="0" />
  <TextBox Grid.Column="1" />
</Grid>`, source: 'https://learn.microsoft.com/en-us/dotnet/api/system.windows.controls.grid' },

  // ── MUI (Material UI for React) ──────────────────────────────────────────────
  { tech: 'mui', title: 'Install MUI (Material UI)', alt: ['telepit'], code: r`npm install @mui/material @emotion/react @emotion/styled`, source: `${MUI}getting-started/installation/` },
  { tech: 'mui', title: 'MUI Button and TextField form', alt: ['gomb', 'urlap'], code: r`import { Button, TextField, Stack } from '@mui/material';

export default function Form() {
  return (
    <Stack spacing={2} sx={{ maxWidth: 320 }}>
      <TextField label="Email" type="email" />
      <Button variant="contained">Send</Button>
    </Stack>
  );
}`, source: `${MUI}react-button/` },
  { tech: 'mui', title: 'MUI dark theme (createTheme and ThemeProvider)', alt: ['tema', 'sotet'], code: r`import { createTheme, ThemeProvider, CssBaseline } from '@mui/material';

const theme = createTheme({
  palette: { mode: 'dark', primary: { main: '#33d6f2' } },
});

<ThemeProvider theme={theme}>
  <CssBaseline />
  <App />
</ThemeProvider>`, source: `${MUI}customization/theming/` },
  { tech: 'mui', title: 'MUI Box with the sx prop', alt: ['stilus'], code: r`import Box from '@mui/material/Box';

<Box sx={{ display: 'flex', gap: 2, p: 2, bgcolor: 'background.paper', borderRadius: 2 }}>
  …
</Box>`, source: `${MUI}react-box/` },
  { tech: 'mui', title: 'MUI Card with Typography', alt: ['kartya'], code: r`import { Card, CardContent, Typography } from '@mui/material';

<Card>
  <CardContent>
    <Typography variant="h5">Title</Typography>
    <Typography color="text.secondary">Some text</Typography>
  </CardContent>
</Card>`, source: `${MUI}react-card/` },

  // ── Bash ─────────────────────────────────────────────────────────────────────
  { tech: 'bash', title: 'Hello world Bash script', alt: ['kiir', 'szkript'], code: r`#!/bin/bash
echo "Hello, World!"
# chmod +x hello.sh && ./hello.sh`, source: BASH },
  { tech: 'bash', title: 'Variables in Bash', alt: ['valtozo'], code: r`name="Auri"              # no spaces around =
echo "Hello, $name"
today=$(date +%F)        # command output into a variable
echo "Today is $today"`, source: BASH },
  { tech: 'bash', title: 'If else in Bash', alt: ['feltetel', 'elagazas'], code: r`if [ -f "config.txt" ]; then
  echo "config exists"
elif [ -d "config" ]; then
  echo "config is a folder"
else
  echo "no config"
fi`, source: BASH },
  { tech: 'bash', title: 'For loop in Bash', alt: ['ciklus'], code: r`for file in *.txt; do
  echo "Found: $file"
done

for i in {1..5}; do echo "$i"; done`, source: BASH },
  { tech: 'bash', title: 'Function in Bash', alt: ['fuggveny'], code: r`greet() {
  echo "Hello, $1"
}
greet "World"`, source: BASH },
  { tech: 'bash', title: 'Script arguments in Bash ($1 $@ $#)', alt: ['parameter', 'argumentum'], code: r`#!/bin/bash
echo "Script: $0"
echo "First arg: $1"
echo "All args: $@"
echo "Count: $#"`, source: BASH },
  { tech: 'bash', title: 'Pipes and grep in Bash', alt: ['kereses', 'szur'], code: r`cat app.log | grep "ERROR" | wc -l   # count error lines
ps aux | grep node                    # find a process`, source: BASH },
  { tech: 'bash', title: 'Read user input in Bash', alt: ['beolvas', 'beker'], code: r`read -p "Your name: " name
echo "Hi $name"`, source: BASH },
  { tech: 'bash', title: 'Read a file line by line in Bash', alt: ['fajl'], code: r`while IFS= read -r line; do
  echo "$line"
done < input.txt`, source: BASH },

  // ── Linux ────────────────────────────────────────────────────────────────────
  { tech: 'linux', title: 'Basic Linux commands (pwd ls cd mkdir)', alt: ['parancs', 'mappa', 'konyvtar'], code: r`pwd              # where am I
ls -la           # list files, hidden ones too
cd /var/log      # change directory
cd ..            # one level up
mkdir projects   # make a folder`, source: `${MAN}man1/ls.1.html` },
  { tech: 'linux', title: 'Copy move delete files in Linux (cp mv rm)', alt: ['masol', 'torol', 'fajl'], code: r`cp a.txt b.txt       # copy
mv b.txt docs/       # move or rename
rm old.txt           # delete a file
rm -r old_folder     # delete a folder
cat notes.txt        # print a file
touch new.txt        # create an empty file`, source: `${MAN}man1/cp.1.html` },
  { tech: 'linux', title: 'Install packages on Linux (apt)', alt: ['telepit', 'csomag'], code: r`sudo apt update
sudo apt upgrade
sudo apt install git curl`, source: 'https://ubuntu.com/server/docs/package-management' },
  { tech: 'linux', title: 'File permissions in Linux (chmod chown)', alt: ['jogosultsag'], code: r`chmod +x script.sh         # make executable
chmod 644 file.txt         # rw-r--r--
sudo chown user:group file.txt`, source: `${MAN}man1/chmod.1.html` },
  { tech: 'linux', title: 'Processes in Linux (ps top kill)', alt: ['folyamat'], code: r`ps aux | grep python
top                 # live view, q to quit
kill 1234           # stop process 1234
kill -9 1234        # force stop`, source: `${MAN}man1/ps.1.html` },
  { tech: 'linux', title: 'Services in Linux (systemctl journalctl)', alt: ['szolgaltatas'], code: r`sudo systemctl status nginx
sudo systemctl restart nginx
sudo systemctl enable nginx    # start on boot
journalctl -u nginx -f         # follow its logs`, source: `${MAN}man1/systemctl.1.html` },
  { tech: 'linux', title: 'Find and search files in Linux (find grep df du)', alt: ['kereses', 'lemez'], code: r`find . -name "*.log"
grep -rn "TODO" src/
du -sh *          # folder sizes
df -h             # free disk space`, source: `${MAN}man1/find.1.html` },
  { tech: 'linux', title: 'SSH into a server from Linux (ssh scp)', alt: ['szerver', 'tavoli'], code: r`ssh user@192.0.2.10
scp file.txt user@192.0.2.10:/home/user/
ssh-keygen -t ed25519            # make a key pair
ssh-copy-id user@192.0.2.10      # log in with the key`, source: `${MAN}man1/ssh.1.html` },
  { tech: 'linux', title: 'Archive with tar in Linux', alt: ['tomorit', 'mentes'], code: r`tar -czf backup.tar.gz folder/   # pack + gzip
tar -xzf backup.tar.gz           # unpack`, source: `${MAN}man1/tar.1.html` },

  // ── Windows (cmd, PowerShell, winget, WSL) ───────────────────────────────────
  { tech: 'windows', title: 'Basic Windows cmd commands (dir cd mkdir copy del)', alt: ['parancs', 'mappa'], code: r`dir
cd C:\Projects
mkdir demo
copy a.txt b.txt
del old.txt
cls`, source: `${WIN}windows-server/administration/windows-commands/windows-commands` },
  { tech: 'windows', title: 'PowerShell basics on Windows', alt: ['parancs'], code: r`Get-ChildItem                   # list files (alias: ls, dir)
Set-Location C:\Projects        # cd
New-Item -ItemType Directory demo
Copy-Item a.txt b.txt
Remove-Item old.txt
Get-Process | Sort-Object CPU -Descending | Select-Object -First 5`, source: `${WIN}powershell/scripting/overview` },
  { tech: 'windows', title: 'PowerShell variables and foreach loop', alt: ['valtozo', 'ciklus'], code: r`$name = "Auri"
Write-Output "Hello, $name"
foreach ($i in 1..3) {
    Write-Output "Round $i"
}`, source: `${WIN}powershell/module/microsoft.powershell.core/about/about_foreach` },
  { tech: 'windows', title: 'PowerShell if else', alt: ['feltetel', 'elagazas'], code: r`if (Test-Path "config.json") {
    Write-Output "config exists"
} else {
    Write-Output "no config"
}`, source: `${WIN}powershell/module/microsoft.powershell.core/about/about_if` },
  { tech: 'windows', title: 'Install apps on Windows with winget', alt: ['telepit'], code: r`winget search vscode
winget install Microsoft.VisualStudioCode
winget upgrade --all`, source: `${WIN}windows/package-manager/winget/` },
  { tech: 'windows', title: 'Network commands on Windows (ipconfig ping)', alt: ['halozat'], code: r`ipconfig /all
ping example.com
tracert example.com
netstat -ano`, source: `${WIN}windows-server/administration/windows-commands/ipconfig` },
  { tech: 'windows', title: 'Install WSL (Linux on Windows)', alt: ['telepit'], code: r`wsl --install      # installs Ubuntu by default
wsl -l -v          # list distributions
wsl                # open the Linux shell`, source: `${WIN}windows/wsl/install` },
  { tech: 'windows', title: 'Windows batch file (.bat)', alt: ['szkript'], code: r`@echo off
echo Hello, World!
set NAME=Auri
echo Hi %NAME%
pause`, source: `${WIN}windows-server/administration/windows-commands/windows-commands` },

  // ── iOS / Swift ──────────────────────────────────────────────────────────────
  { tech: 'ios', title: 'Hello world in Swift', alt: ['kiir'], code: r`print("Hello, World!")`, source: `${SWIFT}thebasics` },
  { tech: 'ios', title: 'Variables in Swift (let and var)', alt: ['valtozo'], code: r`let name = "Ann"      // constant
var count = 0         // variable
count += 1
let pi: Double = 3.14`, source: `${SWIFT}thebasics` },
  { tech: 'ios', title: 'Optionals in Swift (if let, guard let)', alt: ['opcionalis'], code: r`let input: String? = "42"
if let text = input, let n = Int(text) {
    print(n + 1)
}

func load(_ id: Int?) {
    guard let id else { return }
    print(id)
}`, source: `${SWIFT}thebasics#Optionals` },
  { tech: 'ios', title: 'Function in Swift', alt: ['fuggveny'], code: r`func greet(_ name: String, times: Int = 1) -> String {
    String(repeating: "Hi \(name)! ", count: times)
}
print(greet("Ann", times: 2))`, source: `${SWIFT}functions` },
  { tech: 'ios', title: 'Loop and array in Swift', alt: ['ciklus', 'tomb'], code: r`let fruits = ["apple", "pear"]
for fruit in fruits {
    print(fruit)
}
for i in 0..<3 { print(i) }`, source: `${SWIFT}controlflow` },
  { tech: 'ios', title: 'Struct and class in Swift', alt: ['osztaly'], code: r`struct Point { var x: Int; var y: Int }

class Counter {
    var value = 0
    func increment() { value += 1 }
}`, source: `${SWIFT}classesandstructures` },
  { tech: 'ios', title: 'SwiftUI view with state (iOS app)', alt: ['felulet', 'gomb'], code: r`import SwiftUI

struct ContentView: View {
    @State private var count = 0

    var body: some View {
        VStack(spacing: 12) {
            Text("Count: \(count)")
            Button("Add") { count += 1 }
        }
        .padding()
    }
}`, source: 'https://developer.apple.com/tutorials/swiftui' },
  { tech: 'ios', title: 'SwiftUI List (iOS)', alt: ['lista'], code: r`struct FruitList: View {
    let fruits = ["Apple", "Pear", "Plum"]
    var body: some View {
        List(fruits, id: \.self) { Text($0) }
    }
}`, source: 'https://developer.apple.com/documentation/swiftui/list' },

  // ── Go ───────────────────────────────────────────────────────────────────────
  { tech: 'golang', title: 'Hello world in Go (golang)', alt: ['kiir'], code: r`package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}`, source: `${GO}tour/welcome/1` },
  { tech: 'golang', title: 'Variables in Go (golang)', alt: ['valtozo'], code: r`var age int = 30
name := "Ann"      // short declaration
const pi = 3.14`, source: `${GO}tour/basics/8` },
  { tech: 'golang', title: 'For loop and range in Go (golang)', alt: ['ciklus'], code: r`for i := 0; i < 5; i++ {
    fmt.Println(i)
}
for i, v := range []string{"a", "b"} {
    fmt.Println(i, v)
}`, source: `${GO}tour/flowcontrol/1` },
  { tech: 'golang', title: 'Function returning an error in Go (golang)', alt: ['fuggveny', 'hibakezel'], code: r`func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, errors.New("division by zero")
    }
    return a / b, nil
}`, source: `${GO}doc/effective_go#errors` },
  { tech: 'golang', title: 'Struct and method in Go (golang)', alt: ['struktura'], code: r`type User struct {
    Name string
    Age  int
}

func (u User) Greet() string {
    return "Hi, " + u.Name
}`, source: `${GO}tour/methods/1` },
  { tech: 'golang', title: 'Goroutine and channel in Go (golang)', alt: ['parhuzamos'], code: r`ch := make(chan string)
go func() { ch <- "done" }()
fmt.Println(<-ch)`, source: `${GO}tour/concurrency/1` },
  { tech: 'golang', title: 'HTTP server in Go (golang)', alt: ['szerver'], code: r`http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintln(w, "Hello from Go")
})
log.Fatal(http.ListenAndServe(":8080", nil))`, source: 'https://pkg.go.dev/net/http' },
  { tech: 'golang', title: 'Slice and map in Go (golang)', alt: ['tomb', 'szotar'], code: r`nums := []int{1, 2, 3}
nums = append(nums, 4)
ages := map[string]int{"Ann": 30}
ages["Bob"] = 25`, source: `${GO}tour/moretypes/7` },

  // ── Rust ─────────────────────────────────────────────────────────────────────
  { tech: 'rust', title: 'Hello world in Rust', alt: ['kiir'], code: r`fn main() {
    println!("Hello, World!");
}`, source: `${RUST}ch01-02-hello-world.html` },
  { tech: 'rust', title: 'Variables in Rust (let and mut)', alt: ['valtozo'], code: r`let x = 5;          // immutable
let mut y = 10;     // mutable
y += x;
let name: &str = "Ann";`, source: `${RUST}ch03-01-variables-and-mutability.html` },
  { tech: 'rust', title: 'Function in Rust', alt: ['fuggveny'], code: r`fn add(a: i32, b: i32) -> i32 {
    a + b // no semicolon = the return value
}`, source: `${RUST}ch03-03-how-functions-work.html` },
  { tech: 'rust', title: 'Loop over a vector in Rust', alt: ['ciklus', 'tomb'], code: r`let mut nums = vec![1, 2, 3];
nums.push(4);
for n in &nums {
    println!("{n}");
}`, source: `${RUST}ch08-01-vectors.html` },
  { tech: 'rust', title: 'Struct and impl in Rust', alt: ['struktura'], code: r`struct Rect { w: f64, h: f64 }

impl Rect {
    fn area(&self) -> f64 { self.w * self.h }
}`, source: `${RUST}ch05-03-method-syntax.html` },
  { tech: 'rust', title: 'Match and Option in Rust', alt: ['mintaillesztes'], code: r`let maybe: Option<i32> = Some(3);
match maybe {
    Some(n) if n > 2 => println!("big {n}"),
    Some(n) => println!("small {n}"),
    None => println!("nothing"),
}`, source: `${RUST}ch06-02-match.html` },
  { tech: 'rust', title: 'Result and the ? operator in Rust (error handling)', alt: ['hibakezel'], code: r`use std::fs;

fn read_config() -> Result<String, std::io::Error> {
    let text = fs::read_to_string("config.toml")?;
    Ok(text)
}`, source: `${RUST}ch09-02-recoverable-errors-with-result.html` },
  { tech: 'rust', title: 'Ownership and borrowing in Rust', alt: ['tulajdon', 'kolcson'], code: r`fn calc(s: &String) -> usize { s.len() }

let s1 = String::from("hi");
let s2 = s1;           // s1 is MOVED and no longer usable
let len = calc(&s2);   // borrow: s2 stays valid`, source: `${RUST}ch04-01-what-is-ownership.html` },
  { tech: 'rust', title: 'Cargo commands for a Rust project', alt: ['projekt'], code: r`cargo new hello
cd hello
cargo run
cargo build --release
cargo add serde`, source: 'https://doc.rust-lang.org/cargo/' },

  // ── Kotlin ───────────────────────────────────────────────────────────────────
  { tech: 'kotlin', title: 'Hello world in Kotlin', alt: ['kiir'], code: r`fun main() {
    println("Hello, World!")
}`, source: `${KT}basic-syntax.html` },
  { tech: 'kotlin', title: 'Variables in Kotlin (val and var)', alt: ['valtozo'], code: r`val name = "Ann"   // read-only
var count = 0      // mutable
count++`, source: `${KT}basic-syntax.html#variables` },
  { tech: 'kotlin', title: 'When expression in Kotlin', alt: ['feltetel', 'elagazas'], code: r`val label = when (score) {
    in 90..100 -> "excellent"
    in 50..89 -> "passed"
    else -> "failed"
}`, source: `${KT}control-flow.html#when-expressions-and-statements` },
  { tech: 'kotlin', title: 'List and loop in Kotlin', alt: ['lista', 'ciklus'], code: r`val nums = listOf(1, 2, 3)
for (n in nums) println(n)
val doubled = nums.map { it * 2 }`, source: `${KT}collections-overview.html` },

  // ── PHP ──────────────────────────────────────────────────────────────────────
  { tech: 'php', title: 'Hello world in PHP', alt: ['kiir'], code: r`<?php
echo "Hello, World!";`, source: `${PHP}tutorial.firstpage.php` },
  { tech: 'php', title: 'Variables and arrays in PHP', alt: ['valtozo', 'tomb'], code: r`<?php
$name = "Ann";
$ages = ["Ann" => 30, "Bob" => 25];
foreach ($ages as $person => $age) {
    echo "$person is $age\n";
}`, source: `${PHP}language.types.array.php` },
  { tech: 'php', title: 'Function in PHP', alt: ['fuggveny'], code: r`<?php
function add(int $a, int $b): int {
    return $a + $b;
}`, source: `${PHP}language.functions.php` },
  { tech: 'php', title: 'Prepared statement in PHP (PDO, safe from SQL injection)', alt: ['biztonsag', 'lekerdez'], code: r`$stmt = $pdo->prepare('SELECT * FROM users WHERE email = ?');
$stmt->execute([$email]);
$user = $stmt->fetch();`, source: `${PHP}pdo.prepared-statements.php` },

  // ── SQL ──────────────────────────────────────────────────────────────────────
  { tech: 'sql', title: 'SQL UPDATE and DELETE', alt: ['modosit', 'torol'], code: r`UPDATE users SET active = 0 WHERE last_login < '2025-01-01';
DELETE FROM users WHERE id = 42;`, source: `${MYSQL}update.html` },
  { tech: 'sql', title: 'SQL GROUP BY with COUNT', alt: ['csoportosit', 'osszesit'], code: r`SELECT country, COUNT(*) AS users
FROM users
GROUP BY country
HAVING COUNT(*) > 10
ORDER BY users DESC;`, source: `${MYSQL}aggregate-functions.html` },
  { tech: 'sql', title: 'SQL LEFT JOIN', alt: ['osszekapcsol'], code: r`SELECT u.name, o.id AS order_id
FROM users u
LEFT JOIN orders o ON o.user_id = u.id;`, source: `${MYSQL}join.html` },
  { tech: 'sql', title: 'SQL primary key, foreign key and index', alt: ['kulcs', 'index'], code: r`CREATE TABLE orders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX idx_orders_user ON orders(user_id);`, source: `${MYSQL}create-table-foreign-keys.html` },

  // ── VPN ──────────────────────────────────────────────────────────────────────
  { tech: 'vpn', title: 'WireGuard VPN client config', alt: ['beallit', 'konfig'], code: r`[Interface]
PrivateKey = <client-private-key>
Address = 10.8.0.2/24
DNS = 1.1.1.1

[Peer]
PublicKey = <server-public-key>
Endpoint = vpn.example.com:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25`, source: 'https://www.wireguard.com/quickstart/' },
  { tech: 'vpn', title: 'WireGuard VPN keys and tunnel on Linux', alt: ['kulcs', 'indit'], code: r`wg genkey | tee private.key | wg pubkey > public.key
sudo wg-quick up wg0     # start the tunnel
sudo wg show             # status
sudo wg-quick down wg0   # stop it`, source: 'https://www.wireguard.com/quickstart/' },
  { tech: 'vpn', title: 'Connect to an OpenVPN VPN with a config file', alt: ['csatlakoz'], code: r`sudo openvpn --config client.ovpn`, source: 'https://openvpn.net/community-resources/how-to/' },
  { tech: 'vpn', title: 'Check your public IP (is the VPN on?)', alt: ['ellenoriz'], code: r`curl https://ifconfig.me`, source: 'https://www.wireguard.com/quickstart/' },

  // ── WPS Office (spreadsheet formulas, Excel-compatible) ──────────────────────
  { tech: 'wps', title: 'SUM and AVERAGE formula in a WPS or Excel spreadsheet', alt: ['osszeg', 'atlag', 'keplet', 'tablazat'], code: r`=SUM(A1:A10)
=AVERAGE(B2:B20)
=MAX(C2:C100)
=COUNT(A1:A100)`, source: 'https://www.wps.com/' },
  { tech: 'wps', title: 'IF formula in a WPS or Excel spreadsheet', alt: ['feltetel', 'keplet', 'tablazat'], code: r`=IF(B2>=50, "Passed", "Failed")
=IF(AND(B2>=50, C2="yes"), "OK", "Check")`, source: 'https://www.wps.com/' },
  { tech: 'wps', title: 'VLOOKUP formula in a WPS or Excel spreadsheet', alt: ['kereses', 'keplet', 'tablazat'], code: r`=VLOOKUP(E2, A2:C100, 3, FALSE)`, source: 'https://www.wps.com/' },
  { tech: 'wps', title: 'COUNTIF and SUMIF formula in a WPS or Excel spreadsheet', alt: ['szamol', 'keplet', 'tablazat'], code: r`=COUNTIF(A2:A100, "done")
=SUMIF(B2:B100, ">1000", C2:C100)`, source: 'https://www.wps.com/' },
];
