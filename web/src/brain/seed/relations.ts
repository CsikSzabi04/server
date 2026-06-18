// relations.ts — RELATIONAL / "what goes with what" knowledge. The user asked for
// integrated knowledge, not isolated facts: which technologies combine, what pairs
// with what, what a typical stack looks like. Each sentence co-mentions several
// related terms in ONE line, so the learner forms word→word (Markov) + co-occurrence
// edges between them → the association graph CONNECTS the concepts (denser, more
// brain-like /brain map) AND the brain can answer "what works with X".

// English relational sentences (multi-term on purpose → many associations).
export const RELATIONS_EN: string[] = [
  // frontend
  'A website combines HTML for structure, CSS for style and JavaScript for behaviour.',
  'React builds the user interface from components written in JSX, keeps state in hooks like useState and useEffect, and is created with Vite.',
  'React pairs with React Router for pages, a state library like Redux or Zustand for shared state, and Node for the backend.',
  'Vite is the build tool that runs React, Vue and Svelte apps, replacing older bundlers like Webpack and Babel.',
  'Tailwind CSS and Bootstrap are CSS frameworks that style HTML with utility classes and ready-made components.',
  'React Native uses React to build mobile apps for Android and iOS, sharing components across platforms.',
  // node backend
  'Node.js runs JavaScript on the server, pairs with Express for the web framework, uses npm for packages, and talks to a database through an ORM like Prisma or Sequelize.',
  'A Node API uses Express for routes, JSON for data, JWT for authentication, and MySQL or PostgreSQL for storage.',
  // php
  'PHP connects to a MySQL or MariaDB database through PDO, uses Laravel as its framework, Composer for packages, and phpMyAdmin to manage the database in the browser.',
  'WordPress is built with PHP and MySQL, and phpMyAdmin administers its database.',
  // python
  'Python uses pip for packages, Django or Flask for web backends, pandas and NumPy for data, and PyTorch or TensorFlow for AI.',
  'A Python web app pairs Django or Flask with a database like PostgreSQL or MySQL, and serves JSON to a React or Vue frontend.',
  // java / kotlin
  'Java runs on the JVM, builds with Maven or Gradle, uses Spring as its framework, and connects to databases with JPA or Hibernate.',
  'Kotlin runs on the JVM, is fully interoperable with Java, builds with Gradle, and is the main language for Android in Android Studio.',
  // databases
  'SQL is the query language for relational databases like MySQL, PostgreSQL, Oracle and SQLite; you read with SELECT and join tables with JOIN.',
  'An ORM such as Prisma, Sequelize, Hibernate or JPA maps database tables to objects so code can query them without raw SQL.',
  'phpMyAdmin manages MySQL and MariaDB databases in the browser, while Oracle and PostgreSQL have their own tools.',
  // build / tooling
  'npm installs Node packages, pip installs Python packages, Composer installs PHP packages, and Maven or Gradle handle Java and Kotlin.',
  'Git tracks code versions, GitHub hosts the repository, and a CI pipeline tests and deploys it to Vercel, Netlify or a cloud server.',
  // full stack
  'A full-stack web app has a frontend (HTML, CSS, JavaScript, React), a backend (Node, PHP, Python or Java) and a database (MySQL, PostgreSQL or Oracle).',
  'To build a dynamic website you combine a frontend framework like React, a backend like Node or Django, a database like MySQL, and deploy it with Vercel or Docker.',
  'The MERN stack is MongoDB, Express, React and Node; the LAMP stack is Linux, Apache, MySQL and PHP.',
  // AI / company
  'Meta builds React and React Native for interfaces and PyTorch for AI; Google builds TensorFlow, Angular and Go.',
  'An AI app in Python uses PyTorch or TensorFlow for the model, pandas and NumPy for the data, and Flask or FastAPI to serve it.',
  // task-oriented combinations
  'To store data you choose a database (MySQL, PostgreSQL, Oracle), define tables with SQL, and connect from your backend (PHP with PDO, Python with a driver, Node with an ORM).',
  'To make a page interactive you add JavaScript that listens to events and updates the DOM; React does this with state and re-rendering.',
  'To deploy a site you build it with Vite, push to GitHub, and host the result on Vercel, Netlify or GitHub Pages.',
  'For authentication you hash passwords, issue a JWT token on login, and check it on each request.',
  // devops
  'Docker packages an app into a container, Kubernetes runs and scales many containers, and a CI/CD pipeline on GitHub Actions builds, tests and deploys them.',
  'A typical deploy: Git pushes code to GitHub, CI runs the tests, Docker builds an image, and Kubernetes or a platform like Vercel runs it.',
  // mobile
  'Mobile apps are built natively with Kotlin or Java for Android and Swift for iOS, or cross-platform with React Native or Flutter from one codebase.',
  'React Native shares React components across Android and iOS, while Flutter uses Dart; both talk to a backend over a REST API.',
  // ai / ml
  'Machine learning trains a model on a dataset; deep learning uses neural networks with many layers, built in Python with PyTorch or TensorFlow.',
  'A large language model like GPT is a neural network trained on huge text to predict the next word; pandas and NumPy prepare its data.',
  // networking / web protocols
  'The browser uses DNS to find the server, HTTP or HTTPS to request a page, and a REST API that returns JSON for dynamic data.',
  'A web request flows: DNS resolves the domain, HTTPS encrypts the connection, the server returns a response, and JavaScript updates the page.',
  // security
  'Security combines HTTPS encryption, hashed passwords, JWT authentication, and validating every input to block attacks.',
];

// Hungarian mirror of the key relations.
export const RELATIONS_HU: string[] = [
  'Egy weboldal a HTML-t (szerkezet), a CSS-t (stílus) és a JavaScriptet (viselkedés) köti össze.',
  'A React komponensekből épít felületet JSX-ben, az állapotot hookokban (useState, useEffect) tárolja, és Vite-tal indul.',
  'A React a React Routerrel jár az oldalakhoz, egy állapot-könyvtárral (Redux, Zustand) a közös állapothoz, és a Node-dal a backendhez.',
  'A Node.js a szerveren futtat JavaScriptet, az Express a webes keretrendszere, az npm a csomagkezelője, és egy ORM-en (Prisma, Sequelize) át beszél az adatbázissal.',
  'A PHP PDO-n keresztül kapcsolódik MySQL vagy MariaDB adatbázishoz, a Laravel a keretrendszere, a Composer a csomagkezelője, a phpMyAdmin pedig böngészőből kezeli az adatbázist.',
  'A Python pip-pel telepít, Django vagy Flask a webes backendje, a pandas és a NumPy az adathoz, a PyTorch és a TensorFlow az MI-hez való.',
  'A Java a JVM-en fut, Maven vagy Gradle építi, a Spring a keretrendszere, és JPA vagy Hibernate köti az adatbázishoz.',
  'A Kotlin a JVM-en fut, együttműködik a Javával, Gradle-lel épül, és az Android fő nyelve az Android Studióban.',
  'Az SQL a relációs adatbázisok (MySQL, PostgreSQL, Oracle) lekérdező nyelve; SELECT-tel olvasol, JOIN-nal kapcsolsz táblákat.',
  'Egy teljes webalkalmazásnak van frontendje (HTML, CSS, JavaScript, React), backendje (Node, PHP, Python, Java) és adatbázisa (MySQL, PostgreSQL, Oracle).',
  'Dinamikus weboldalhoz egy frontend keretrendszert (React), egy backendet (Node vagy Django), egy adatbázist (MySQL) kombinálsz, és Vercellel vagy Dockerrel telepítesz.',
  'Adat tárolásához választasz egy adatbázist (MySQL, PostgreSQL, Oracle), SQL-lel táblákat hozol létre, és a backendből kapcsolódsz (PHP PDO-val, Python driverrel, Node ORM-mel).',
];

// Combination Q→A — "what goes with X / what works together".
export const RELATIONS_QA: [string, string][] = [
  ['what works with react', 'React works with JSX, hooks, React Router, Vite, and a Node backend.'],
  ['mi megy a reacttal', 'A React JSX-szel, hookokkal, React Routerrel, Vite-tal és egy Node backenddel megy.'],
  ['what database goes with php', 'PHP usually pairs with MySQL or MariaDB through PDO, managed with phpMyAdmin.'],
  ['what do i use with node', 'Node pairs with Express for routes, npm for packages, and an ORM like Prisma for the database.'],
  ['what stack for a web app', 'A common stack: React or Vue frontend, Node, PHP or Python backend, and MySQL or PostgreSQL database.'],
  ['what works with python', 'Python works with pip, Django or Flask for web, pandas and NumPy for data, and PyTorch or TensorFlow for AI.'],
  ['what builds react apps', 'Vite builds React (and Vue and Svelte) apps and replaces older bundlers like Webpack.'],
  ['what connects php to mysql', 'PDO connects PHP to a MySQL or MariaDB database.'],
  ['what is the mern stack', 'MERN is MongoDB, Express, React and Node — a full JavaScript web stack.'],
  ['what is the lamp stack', 'LAMP is Linux, Apache, MySQL and PHP — a classic web server stack.'],
  ['what builds java projects', 'Maven or Gradle build Java and Kotlin projects; Spring is the common framework.'],
  ['mi kell egy weboldalhoz', 'Frontend (HTML, CSS, JavaScript vagy React), backend (Node, PHP vagy Python) és adatbázis (MySQL).'],
];
