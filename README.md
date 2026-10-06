# 🎬 Movie Collaboration Explorer

An interactive graph visualisation application that explores how actors are connected through movie collaborations.

The project represents actors as nodes and movie collaborations as edges, allowing users to investigate collaboration strength, communities, centrality, genres and changes over time.

---

##  Project Overview

The movie industry can be represented as a collaboration network.

In this project:

- Each **actor** is represented as a node.
- An **edge** connects two actors when they appear in the same movie.
- The **edge weight** represents the number of movies shared by two actors.
- The **node size** represents the number of direct actor connections.
- The **node colour** represents a detected community.
- The **network position** is determined using a force-directed layout.

The application allows users to interactively explore this network through filtering, searching and network analysis.

---

##  Objectives

The main objectives of this project are:

1. Explore actor relationships through movie collaborations.
2. Identify actors with a high number of direct connections.
3. Find the strongest actor collaborations.
4. Detect communities within the actor network.
5. Identify actors that act as bridges between network groups.
6. Analyse how the network changes over time.
7. Compare collaboration networks across movie genres.
8. Provide an interactive visualisation for exploring the network.

---

##  Questions Answered

The application helps answer questions such as:

- How are actors connected through movies?
- Which actors have the most direct collaborators?
- Which pairs of actors have worked together most frequently?
- Which communities exist in the actor network?
- Which actors act as bridges between different groups?
- How does the collaboration network change over time?
- How does collaboration differ across movie genres?
- How does filtering change the structure of the network?

---

##  Dataset

The project uses the **TMDB 5000 Movie Dataset**.

The dataset contains information about movies, including:

- Movie title
- Release date
- Genres
- Cast
- Crew
- Movie ID

Two CSV files are used:

```text
data/
├── tmdb_5000_credits.csv
└── tmdb_5000_movies.csv