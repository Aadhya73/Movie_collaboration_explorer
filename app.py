import streamlit as st
import pandas as pd
import networkx as nx
import json
import itertools
from pyvis.network import Network
import streamlit.components.v1 as components


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Movie Collaboration Explorer",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 42px;
        font-weight: 700;
        margin-bottom: 0px;
    }

    .subtitle {
        font-size: 18px;
        color: #9ca3af;
        margin-top: 4px;
        margin-bottom: 20px;
    }

    .info-box {
        padding: 16px 20px;
        border-left: 4px solid #ff4b4b;
        background-color: rgba(255, 75, 75, 0.08);
        border-radius: 7px;
        margin-bottom: 20px;
    }

    .section-title {
        font-size: 27px;
        font-weight: 600;
        margin-top: 15px;
        margin-bottom: 10px;
    }

    .actor-header {
        padding: 20px;
        border-radius: 10px;
        background: linear-gradient(
            135deg,
            rgba(255, 75, 75, 0.14),
            rgba(80, 80, 255, 0.08)
        );
        border: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 20px;
    }

    .actor-name {
        font-size: 32px;
        font-weight: 700;
    }

    .feature-card {
        padding: 18px;
        border-radius: 10px;
        background-color: rgba(255,255,255,0.035);
        border: 1px solid rgba(255,255,255,0.08);
        min-height: 120px;
    }

    .feature-card h4 {
        margin-top: 0px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">🎬 Movie Collaboration Explorer</div>',
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="subtitle">
        Exploring actor relationships through movies, genres and time
        using interactive graph visualisation.
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="info-box">
        <b>How does this visualisation work?</b><br><br>
        Each actor is represented as a <b>node</b>.
        Two actors are connected when they appear in the same movie.
        The number of movies shared by two actors determines the
        <b>strength of their collaboration</b>.
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# LOAD DATA
# =========================================================

@st.cache_data
def load_data():

    credits = pd.read_csv(
        "data/tmdb_5000_credits.csv"
    )

    movies = pd.read_csv(
        "data/tmdb_5000_movies.csv"
    )

    data = movies.merge(
        credits,
        left_on="id",
        right_on="movie_id",
        how="inner",
        suffixes=("_movie", "_credit")
    )

    # Keep one clear movie title column
    if "title_movie" in data.columns:
        data["movie_title"] = data["title_movie"]
    elif "title" in data.columns:
        data["movie_title"] = data["title"]
    else:
        data["movie_title"] = "Unknown Movie"

    return data


try:

    data = load_data()

except Exception as e:

    st.error("Unable to load the dataset.")
    st.code(str(e))
    st.stop()


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def parse_json(value):

    try:

        if pd.isna(value):
            return []

        return json.loads(value)

    except Exception:

        return []


def extract_cast(cast_string, max_actors=8):

    cast = parse_json(cast_string)

    actors = []

    for person in cast[:max_actors]:

        if isinstance(person, dict):

            name = person.get("name")

            if name:
                actors.append(name)

    return actors


def extract_genres(genre_string):

    genres = parse_json(genre_string)

    result = []

    for genre in genres:

        if isinstance(genre, dict):

            name = genre.get("name")

            if name:
                result.append(name)

    return result


# =========================================================
# DATA PREPROCESSING
# =========================================================

data["release_date"] = pd.to_datetime(
    data["release_date"],
    errors="coerce"
)

data["year"] = data["release_date"].dt.year

data["genre_list"] = data["genres"].apply(
    extract_genres
)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.markdown(
    """
    # 🎛️ Explore Network

    Use these controls to explore different parts
    of the actor collaboration network.
    """
)

st.sidebar.divider()


# =========================================================
# YEAR FILTER
# =========================================================

st.sidebar.markdown("### 📅 Time")

valid_years = data["year"].dropna()

if len(valid_years) > 0:

    min_year = int(valid_years.min())
    max_year = int(valid_years.max())

else:

    min_year = 1900
    max_year = 2025


default_start = max(
    min_year,
    2000
)

year_range = st.sidebar.slider(
    "Release Year",
    min_value=min_year,
    max_value=max_year,
    value=(default_start, max_year)
)


# =========================================================
# GENRE FILTER
# =========================================================

st.sidebar.markdown("### 🎭 Genre")

all_genres = sorted(
    set(
        genre
        for genres in data["genre_list"]
        for genre in genres
    )
)

selected_genres = st.sidebar.multiselect(
    "Select genre(s)",
    all_genres,
    default=[]
)


# =========================================================
# NETWORK FILTERS
# =========================================================

st.sidebar.markdown("### 🔗 Network")

min_collaboration = st.sidebar.slider(
    "Minimum shared movies",
    min_value=1,
    max_value=5,
    value=2,
    help="Only show actor pairs who worked together at least this many times."
)

actors_per_movie = st.sidebar.slider(
    "Actors considered per movie",
    min_value=3,
    max_value=10,
    value=8,
    help="Number of top-billed actors considered from each movie."
)

max_nodes = st.sidebar.slider(
    "Maximum actors displayed",
    min_value=30,
    max_value=200,
    value=100,
    help="Limits the network size to reduce visual clutter."
)


# =========================================================
# ACTOR EXTRACTION
# =========================================================

data["actor_list"] = data["cast"].apply(
    lambda x: extract_cast(
        x,
        actors_per_movie
    )
)


# =========================================================
# APPLY MAIN FILTERS
# =========================================================

filtered_data = data[
    (data["year"] >= year_range[0]) &
    (data["year"] <= year_range[1])
].copy()


if selected_genres:

    filtered_data = filtered_data[
        filtered_data["genre_list"].apply(
            lambda genres:
            any(
                genre in genres
                for genre in selected_genres
            )
        )
    ]


# =========================================================
# BUILD GRAPH
# =========================================================

@st.cache_data
def build_graph(movie_data, minimum_collaboration):

    G = nx.Graph()

    for _, movie in movie_data.iterrows():

        actors = movie["actor_list"]

        actors = list(
            dict.fromkeys(actors)
        )

        if len(actors) == 0:
            continue

        movie_title = movie.get(
            "movie_title",
            "Unknown Movie"
        )

        # Add actor nodes
        for actor in actors:

            if not G.has_node(actor):

                G.add_node(
                    actor,
                    movies=[]
                )

            G.nodes[actor]["movies"].append(
                movie_title
            )

        # Create actor pairs
        for actor1, actor2 in itertools.combinations(
            actors,
            2
        ):

            if G.has_edge(
                actor1,
                actor2
            ):

                G[actor1][actor2]["weight"] += 1

                G[actor1][actor2]["movies"].append(
                    movie_title
                )

            else:

                G.add_edge(
                    actor1,
                    actor2,
                    weight=1,
                    movies=[movie_title]
                )

    # Remove weak collaborations
    edges_to_remove = [
        (u, v)
        for u, v, attributes in G.edges(
            data=True
        )
        if attributes["weight"] < minimum_collaboration
    ]

    G.remove_edges_from(
        edges_to_remove
    )

    # Remove isolated actors
    isolated_nodes = list(
        nx.isolates(G)
    )

    G.remove_nodes_from(
        isolated_nodes
    )

    return G


G_full = build_graph(
    filtered_data,
    min_collaboration
)


# =========================================================
# LIMIT DISPLAYED NETWORK
# =========================================================

G = G_full.copy()

if len(G.nodes) > max_nodes:

    important_nodes = sorted(
        G.degree,
        key=lambda x: x[1],
        reverse=True
    )[:max_nodes]

    important_nodes = [
        node
        for node, degree in important_nodes
    ]

    G = G.subgraph(
        important_nodes
    ).copy()


# =========================================================
# COMMUNITY DETECTION
# =========================================================

if len(G.nodes) > 1:

    try:

        communities = list(
            nx.community.greedy_modularity_communities(
                G,
                weight="weight"
            )
        )

    except Exception:

        communities = []

else:

    communities = []


community_map = {}

for community_id, community in enumerate(
    communities
):

    for actor in community:

        community_map[actor] = community_id


# =========================================================
# CENTRALITY
# =========================================================

if len(G.nodes) > 1:

    degree_centrality = nx.degree_centrality(
        G
    )

    betweenness_centrality = nx.betweenness_centrality(
        G,
        normalized=True
    )

else:

    degree_centrality = {}
    betweenness_centrality = {}


# =========================================================
# NETWORK STATISTICS
# =========================================================

number_of_actors = len(
    G.nodes
)

number_of_connections = len(
    G.edges
)

number_of_movies = len(
    filtered_data
)

if number_of_actors > 1:

    density = nx.density(
        G
    )

else:

    density = 0


if number_of_actors > 0:

    average_degree = (
        sum(
            dict(G.degree()).values()
        )
        / number_of_actors
    )

else:

    average_degree = 0


number_of_communities = len(
    communities
)


if number_of_actors > 0:

    most_connected_actor = max(
        G.degree,
        key=lambda x: x[1]
    )

else:

    most_connected_actor = (
        "None",
        0
    )


# =========================================================
# DEGREE DATA
# =========================================================

degree_data = pd.DataFrame(
    G.degree,
    columns=[
        "Actor",
        "Connections"
    ]
)

if not degree_data.empty:

    degree_data = degree_data.sort_values(
        "Connections",
        ascending=False
    )


# =========================================================
# CENTRALITY DATA
# =========================================================

centrality_data = pd.DataFrame(
    [
        {
            "Actor": actor,
            "Degree Centrality": degree_centrality.get(
                actor,
                0
            ),
            "Betweenness Centrality": betweenness_centrality.get(
                actor,
                0
            )
        }
        for actor in G.nodes()
    ]
)

if not centrality_data.empty:

    centrality_data = centrality_data.sort_values(
        "Betweenness Centrality",
        ascending=False
    )


# =========================================================
# STRONGEST COLLABORATIONS
# =========================================================

strongest_collaborations = []

for actor1, actor2, attributes in G.edges(
    data=True
):

    strongest_collaborations.append(
        {
            "Actor 1": actor1,
            "Actor 2": actor2,
            "Shared Movies": attributes["weight"]
        }
    )


strongest_collaborations_df = pd.DataFrame(
    strongest_collaborations
)

if not strongest_collaborations_df.empty:

    strongest_collaborations_df = (
        strongest_collaborations_df
        .sort_values(
            "Shared Movies",
            ascending=False
        )
    )


# =========================================================
# ACTOR SEARCH
# =========================================================

st.sidebar.divider()

st.sidebar.markdown("### 🔎 Actor Search")

actor_names = sorted(
    G.nodes()
)

search_text = st.sidebar.text_input(
    "Search actor",
    placeholder="e.g. Leonardo DiCaprio"
)


if search_text:

    matching_actors = [
        actor
        for actor in actor_names
        if search_text.lower()
        in actor.lower()
    ]

else:

    matching_actors = actor_names


if matching_actors:

    selected_actor = st.sidebar.selectbox(
        "Select actor",
        ["None"] + matching_actors
    )

else:

    selected_actor = "None"

    st.sidebar.warning(
        "No matching actor found."
    )


# =========================================================
# TABS
# =========================================================

tab_overview, tab_network, tab_actor, tab_analysis = st.tabs(
    [
        "📊 Overview",
        "🕸️ Network",
        "👤 Actor Explorer",
        "📈 Analysis"
    ]
)


# =========================================================
# TAB 1 — OVERVIEW
# =========================================================

with tab_overview:

    st.markdown(
        '<div class="section-title">📊 Network Overview</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # MAIN METRICS
    # -----------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "👥 Actors",
            number_of_actors
        )

    with col2:

        st.metric(
            "🔗 Connections",
            number_of_connections
        )

    with col3:

        st.metric(
            "🎬 Movies",
            number_of_movies
        )

    with col4:

        st.metric(
            "📊 Density",
            f"{density:.3f}"
        )


    col5, col6, col7 = st.columns(3)

    with col5:

        st.metric(
            "🏘️ Communities",
            number_of_communities
        )

    with col6:

        st.metric(
            "📐 Average Degree",
            f"{average_degree:.2f}"
        )

    with col7:

        st.metric(
            "⭐ Most Connected",
            most_connected_actor[0]
        )


    st.divider()


    # -----------------------------------------------------
    # FEATURE GUIDE
    # -----------------------------------------------------

    st.markdown(
        "### 🧭 Explore the Project"
    )

    guide1, guide2, guide3, guide4 = st.columns(4)

    with guide1:

        st.markdown(
            """
            <div class="feature-card">
            <h4>🕸️ Network</h4>
            Explore actor connections,
            communities and collaboration strength.
            </div>
            """,
            unsafe_allow_html=True
        )

    with guide2:

        st.markdown(
            """
            <div class="feature-card">
            <h4>👤 Actor Explorer</h4>
            Select an actor and investigate
            their personal collaboration network.
            </div>
            """,
            unsafe_allow_html=True
        )

    with guide3:

        st.markdown(
            """
            <div class="feature-card">
            <h4>🏘️ Communities</h4>
            Discover groups of actors
            who are strongly connected.
            </div>
            """,
            unsafe_allow_html=True
        )

    with guide4:

        st.markdown(
            """
            <div class="feature-card">
            <h4>📈 Analysis</h4>
            Compare networks across
            time and movie genres.
            </div>
            """,
            unsafe_allow_html=True
        )


    st.divider()


    # -----------------------------------------------------
    # TOP ACTORS + STRONGEST COLLABORATIONS
    # -----------------------------------------------------

    left_col, right_col = st.columns(2)

    with left_col:

        st.markdown(
            "### 🏆 Most Connected Actors"
        )

        if not degree_data.empty:

            chart_data = (
                degree_data
                .head(10)
                .set_index("Actor")
            )

            st.bar_chart(
                chart_data
            )

        else:

            st.info(
                "No actor data available."
            )


    with right_col:

        st.markdown(
            "### 💪 Strongest Collaborations"
        )

        if not strongest_collaborations_df.empty:

            st.dataframe(
                strongest_collaborations_df.head(10),
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "No collaboration data available."
            )


    # -----------------------------------------------------
    # CENTRALITY
    # -----------------------------------------------------

    st.markdown(
        "### 🌉 Network Bridge Actors"
    )

    st.caption(
        "Betweenness centrality identifies actors that "
        "can connect otherwise separate parts of the network."
    )

    if not centrality_data.empty:

        display_centrality = centrality_data.copy()

        display_centrality[
            "Degree Centrality"
        ] = display_centrality[
            "Degree Centrality"
        ].round(3)

        display_centrality[
            "Betweenness Centrality"
        ] = display_centrality[
            "Betweenness Centrality"
        ].round(3)

        st.dataframe(
            display_centrality.head(10),
            use_container_width=True,
            hide_index=True
        )


    # -----------------------------------------------------
    # AUTOMATIC INSIGHTS
    # -----------------------------------------------------

    st.markdown(
        "### 💡 Network Insights"
    )

    if number_of_actors > 0:

        st.markdown(
            f"""
            🔹 The current network contains
            **{number_of_actors} actors** and
            **{number_of_connections} collaboration edges**.

            🔹 **{most_connected_actor[0]}** has the highest
            number of direct connections with
            **{most_connected_actor[1]} collaborators**.

            🔹 The network contains
            **{number_of_communities} detected communities**.

            🔹 The average actor has approximately
            **{average_degree:.2f} direct connections**.
            """
        )

        if not strongest_collaborations_df.empty:

            strongest = (
                strongest_collaborations_df.iloc[0]
            )

            st.markdown(
                f"""
                🔹 The strongest observed collaboration is
                between **{strongest['Actor 1']}** and
                **{strongest['Actor 2']}**, with
                **{strongest['Shared Movies']} shared movies**.
                """
            )

    else:

        st.warning(
            "No network available with the current filters."
        )


# =========================================================
# TAB 2 — NETWORK
# =========================================================

with tab_network:

    st.markdown(
        '<div class="section-title">🕸️ Actor Collaboration Network</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Node size = number of direct connections | "
        "Edge thickness = collaboration strength | "
        "Colour = community"
    )


    if len(G.nodes) == 0:

        st.warning(
            "No actors found with the current filters. "
            "Try reducing the minimum shared movies value "
            "or changing the year/genre filters."
        )

    else:

        community_colours = [
            "#ff6b6b",
            "#4dabf7",
            "#51cf66",
            "#fcc419",
            "#845ef7",
            "#20c997",
            "#ff922b",
            "#e64980",
            "#15aabf",
            "#94d82d"
        ]


        net = Network(
            height="700px",
            width="100%",
            bgcolor="#111827",
            font_color="white",
            notebook=False,
            cdn_resources="in_line"
        )


        net.barnes_hut(
            gravity=-3000,
            central_gravity=0.3,
            spring_length=150,
            spring_strength=0.02,
            damping=0.09
        )


        # -------------------------------------------------
        # NODES
        # -------------------------------------------------

        for actor in G.nodes():

            degree = G.degree(
                actor
            )

            community = community_map.get(
                actor,
                0
            )

            node_colour = community_colours[
                community %
                len(community_colours)
            ]

            movie_count = len(
                set(
                    G.nodes[actor].get(
                        "movies",
                        []
                    )
                )
            )

            node_size = (
                12 +
                (degree ** 0.8) * 8
            )

            title = f"""
            <b>{actor}</b><br>
            Connections: {degree}<br>
            Movies in current network: {movie_count}<br>
            Community: {community + 1}<br>
            Degree centrality:
            {degree_centrality.get(actor, 0):.3f}<br>
            Betweenness:
            {betweenness_centrality.get(actor, 0):.3f}
            """

            net.add_node(
                actor,
                label=actor,
                size=node_size,
                title=title,
                group=community,
                color=node_colour
            )


        # -------------------------------------------------
        # EDGES
        # -------------------------------------------------

        for actor1, actor2, attributes in G.edges(
            data=True
        ):

            weight = attributes[
                "weight"
            ]

            movie_names = attributes.get(
                "movies",
                []
            )

            unique_movies = list(
                dict.fromkeys(
                    movie_names
                )
            )

            movie_text = "<br>".join(
                unique_movies[:8]
            )

            title = f"""
            <b>Collaboration</b><br>
            {actor1} + {actor2}<br>
            Shared movies: {weight}<br><br>
            {movie_text}
            """

            edge_width = min(
                8,
                1 + weight * 1.2
            )

            net.add_edge(
                actor1,
                actor2,
                value=weight,
                width=edge_width,
                title=title
            )


        # -------------------------------------------------
        # HIGHLIGHT SELECTED ACTOR
        # -------------------------------------------------

        if selected_actor != "None":

            for node in net.nodes:

                if node["id"] == selected_actor:

                    node["color"] = "#ffcc00"
                    node["size"] = 38


        # IMPORTANT:
        # generate_html() avoids the Windows
        # UnicodeEncodeError caused by save_graph().
        html = net.generate_html()

        components.html(
            html,
            height=720,
            scrolling=True
        )


    # -----------------------------------------------------
    # GRAPH LEGEND
    # -----------------------------------------------------

    st.markdown(
        "### 📚 How to Read the Network"
    )

    legend_col1, legend_col2, legend_col3 = st.columns(3)

    with legend_col1:

        st.markdown(
            """
            **● Node**

            Represents an actor.

            **Larger node**

            More direct collaborators.
            """
        )

    with legend_col2:

        st.markdown(
            """
            **━━ Edge**

            Represents a movie collaboration.

            **Thicker edge**

            Actors shared more movies.
            """
        )

    with legend_col3:

        st.markdown(
            """
            **🎨 Colour**

            Represents a detected community.

            **📍 Position**

            Related actors tend to cluster together.
            """
        )


# =========================================================
# TAB 3 — ACTOR EXPLORER
# =========================================================

with tab_actor:

    st.markdown(
        '<div class="section-title">👤 Actor Explorer</div>',
        unsafe_allow_html=True
    )


    if selected_actor == "None":

        st.info(
            "Use the Actor Search in the sidebar to select "
            "an actor and explore their collaboration network."
        )

        st.markdown(
            """
            ### 🔎 What can you investigate?

            **Connections**  
            How many direct collaborators does the actor have?

            **Degree Centrality**  
            How connected is the actor compared with other actors?

            **Betweenness Centrality**  
            Does the actor act as a bridge between different groups?

            **Ego Network**  
            Who are the actor's immediate collaborators?

            **Strongest Collaborator**  
            Who has the most shared movies with the selected actor?
            """
        )

    else:

        # =================================================
        # ACTOR DATA
        # =================================================

        actor_degree = G.degree(
            selected_actor
        )

        neighbours = list(
            G.neighbors(
                selected_actor
            )
        )

        actor_movies = set(
            G.nodes[selected_actor].get(
                "movies",
                []
            )
        )

        actor_degree_centrality = (
            degree_centrality.get(
                selected_actor,
                0
            )
        )

        actor_betweenness = (
            betweenness_centrality.get(
                selected_actor,
                0
            )
        )

        actor_community = (
            community_map.get(
                selected_actor,
                0
            ) + 1
        )


        # =================================================
        # ACTOR COLLABORATIONS
        # =================================================

        collaborator_data = []

        for collaborator in neighbours:

            shared_movies = G[
                selected_actor
            ][
                collaborator
            ]["weight"]

            collaborator_data.append(
                {
                    "Actor": collaborator,
                    "Shared Movies": shared_movies
                }
            )

        collaborator_df = pd.DataFrame(
            collaborator_data
        )

        if not collaborator_df.empty:

            collaborator_df = (
                collaborator_df
                .sort_values(
                    "Shared Movies",
                    ascending=False
                )
            )


        # =================================================
        # STRONGEST COLLABORATOR
        # =================================================

        if not collaborator_df.empty:

            strongest_collaborator = (
                collaborator_df.iloc[0]["Actor"]
            )

            strongest_shared_movies = int(
                collaborator_df.iloc[0]["Shared Movies"]
            )

        else:

            strongest_collaborator = "None"
            strongest_shared_movies = 0


        # =================================================
        # ACTOR HEADER
        # =================================================

        st.markdown(
            f"""
            <div class="actor-header">

            <div class="actor-name">
            🎭 {selected_actor}
            </div>

            <div style="color:#9ca3af; margin-top:6px;">
            Actor collaboration profile in the
            currently filtered network
            </div>

            </div>
            """,
            unsafe_allow_html=True
        )


        # =================================================
        # ACTOR METRICS
        # =================================================

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.metric(
                "🔗 Connections",
                actor_degree
            )

        with col2:

            st.metric(
                "🎬 Movies",
                len(actor_movies)
            )

        with col3:

            st.metric(
                "📊 Degree Centrality",
                f"{actor_degree_centrality:.3f}"
            )

        with col4:

            st.metric(
                "🌉 Betweenness",
                f"{actor_betweenness:.3f}"
            )


        # =================================================
        # ACTOR SUMMARY
        # =================================================

        st.info(
            f"**{selected_actor}** belongs to "
            f"**Community {actor_community}**. "
            f"They have **{actor_degree} direct collaborators** "
            f"in the current network."
        )


        # =================================================
        # ACTOR INSIGHT
        # =================================================

        if strongest_collaborator != "None":

            st.success(
                f"💡 **Strongest collaboration:** "
                f"{selected_actor} has worked most frequently "
                f"with **{strongest_collaborator}**, sharing "
                f"**{strongest_shared_movies} movies** "
                f"in the current network."
            )


        st.divider()


        # =================================================
        # EGO NETWORK
        # =================================================

        st.markdown(
            f"### 🕸️ {selected_actor}'s Collaboration Network"
        )

        st.caption(
            "This ego network shows the selected actor "
            "and their immediate collaborators."
        )


        ego_graph = nx.ego_graph(
            G,
            selected_actor,
            radius=1
        )


        if len(ego_graph.nodes) > 1:

            ego_net = Network(
                height="580px",
                width="100%",
                bgcolor="#111827",
                font_color="white",
                notebook=False,
                cdn_resources="in_line"
            )


            ego_net.barnes_hut(
                gravity=-3000,
                central_gravity=0.3,
                spring_length=150,
                spring_strength=0.02,
                damping=0.09
            )


            for actor in ego_graph.nodes():

                degree = ego_graph.degree(
                    actor
                )

                if actor == selected_actor:

                    ego_net.add_node(
                        actor,
                        label=actor,
                        size=42,
                        color="#ffcc00",
                        title=f"""
                        <b>{actor}</b><br>
                        Selected Actor<br>
                        Connections: {actor_degree}
                        """
                    )

                else:

                    ego_net.add_node(
                        actor,
                        label=actor,
                        size=15 + degree * 2,
                        title=f"""
                        <b>{actor}</b><br>
                        Connection within ego network: {degree}
                        """
                    )


            for actor1, actor2, attributes in ego_graph.edges(
                data=True
            ):

                weight = attributes[
                    "weight"
                ]

                ego_net.add_edge(
                    actor1,
                    actor2,
                    value=weight,
                    width=min(
                        8,
                        1 + weight * 1.2
                    ),
                    title=f"Shared movies: {weight}"
                )


            ego_html = ego_net.generate_html()

            components.html(
                ego_html,
                height=600,
                scrolling=True
            )

        else:

            st.warning(
                "Not enough connections to create "
                "an ego network."
            )


        # =================================================
        # TOP COLLABORATORS
        # =================================================

        st.markdown(
            "### 🤝 Top Collaborators"
        )

        if not collaborator_df.empty:

            st.dataframe(
                collaborator_df.head(15),
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "No collaborators found."
            )


        # =================================================
        # COLLABORATOR CHART
        # =================================================

        if not collaborator_df.empty:

            st.markdown(
                "### 📊 Collaboration Strength"
            )

            collaborator_chart = (
                collaborator_df
                .head(10)
                .set_index("Actor")
            )

            st.bar_chart(
                collaborator_chart
            )


        # =================================================
        # MOVIES
        # =================================================

        st.markdown(
            "### 🎬 Movies in Current Network"

        )

        actor_movie_df = pd.DataFrame(
            {
                "Movie": sorted(
                    actor_movies
                )
            }
        )

        if not actor_movie_df.empty:

            st.dataframe(
                actor_movie_df,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "No movie information available."
            )


        # =================================================
        # CENTRALITY EXPLANATION
        # =================================================

        with st.expander(
            "📚 What do these centrality measures mean?"
        ):

            st.markdown(
                f"""
                **Degree Centrality = {actor_degree_centrality:.3f}**

                Measures how strongly connected this actor is
                through their direct relationships.

                A higher value means the actor has connections
                to a larger proportion of actors in the network.

                ---

                **Betweenness Centrality = {actor_betweenness:.3f}**

                Measures how often an actor lies on shortest
                paths connecting other actors.

                A higher value can indicate that the actor
                plays a **bridge role** between different
                parts of the network.

                ---

                **Important:**

                These measures describe the actor's structural
                position in this network. They do not by
                themselves prove real-world fame or influence.
                """
            )


# =========================================================
# TAB 4 — ANALYSIS
# =========================================================

with tab_analysis:

    st.markdown(
        '<div class="section-title">📈 Network Analysis</div>',
        unsafe_allow_html=True
    )


    # =====================================================
    # NETWORK OVER TIME
    # =====================================================

    st.markdown(
        "### 📅 Network Over Time"
    )

    st.caption(
        "Explore how the collaboration network changes "
        "across different time periods."
    )


    time_range = st.slider(
        "Select time period",
        min_value=min_year,
        max_value=max_year,
        value=(
            min_year,
            max_year
        ),
        key="time_analysis_slider"
    )


    time_data = data[
        (data["year"] >= time_range[0]) &
        (data["year"] <= time_range[1])
    ].copy()


    time_graph = build_graph(
        time_data,
        min_collaboration
    )


    time_col1, time_col2 = st.columns(2)

    with time_col1:

        st.metric(
            "👥 Actors in Period",
            len(time_graph.nodes)
        )

    with time_col2:

        st.metric(
            "🔗 Connections in Period",
            len(time_graph.edges)
        )


    # =====================================================
    # NETWORK GROWTH
    # =====================================================

    st.markdown(
        "### 📈 Network Growth"
    )

    available_years = sorted(
        data["year"]
        .dropna()
        .unique()
    )


    if len(available_years) > 0:

        if len(available_years) > 20:

            step = max(
                1,
                len(available_years) // 20
            )

            analysis_years = list(
                available_years[::step]
            )

            if available_years[-1] not in analysis_years:

                analysis_years.append(
                    available_years[-1]
                )

        else:

            analysis_years = list(
                available_years
            )


        year_statistics = []


        for year in analysis_years:

            yearly_data = data[
                data["year"] <= year
            ].copy()


            yearly_graph = build_graph(
                yearly_data,
                1
            )


            year_statistics.append(
                {
                    "Year": int(year),
                    "Actors": len(
                        yearly_graph.nodes
                    ),
                    "Connections": len(
                        yearly_graph.edges
                    )
                }
            )


        year_statistics_df = pd.DataFrame(
            year_statistics
        )


        if not year_statistics_df.empty:

            st.line_chart(
                year_statistics_df.set_index(
                    "Year"
                )
            )


    # =====================================================
    # GENRE ANALYSIS
    # =====================================================

    st.divider()

    st.markdown(
        "### 🎭 Genre Analysis"
    )

    st.caption(
        "Compare how actor collaboration networks "
        "differ across movie genres."
    )


    genre_comparison = []


    for genre in all_genres:

        genre_data = data[
            data["genre_list"].apply(
                lambda genres:
                genre in genres
            )
        ].copy()


        genre_data = genre_data[
            (genre_data["year"] >= year_range[0]) &
            (genre_data["year"] <= year_range[1])
        ]


        genre_graph = build_graph(
            genre_data,
            min_collaboration
        )


        genre_nodes = len(
            genre_graph.nodes
        )

        genre_edges = len(
            genre_graph.edges
        )


        if genre_nodes > 1:

            genre_density = nx.density(
                genre_graph
            )

        else:

            genre_density = 0


        genre_comparison.append(
            {
                "Genre": genre,
                "Actors": genre_nodes,
                "Connections": genre_edges,
                "Density": genre_density
            }
        )


    genre_comparison_df = pd.DataFrame(
        genre_comparison
    )


    if not genre_comparison_df.empty:

        # -------------------------------------------------
        # SUMMARY
        # -------------------------------------------------

        largest_genre = genre_comparison_df.loc[
            genre_comparison_df["Actors"].idxmax()
        ]

        most_connected_genre = genre_comparison_df.loc[
            genre_comparison_df["Connections"].idxmax()
        ]

        densest_genre = genre_comparison_df.loc[
            genre_comparison_df["Density"].idxmax()
        ]


        col1, col2, col3 = st.columns(3)


        with col1:

            st.metric(
                "👥 Largest Actor Network",
                largest_genre["Genre"],
                f"{int(largest_genre['Actors'])} actors"
            )


        with col2:

            st.metric(
                "🔗 Most Connections",
                most_connected_genre["Genre"],
                f"{int(most_connected_genre['Connections'])} connections"
            )


        with col3:

            st.metric(
                "📊 Highest Density",
                densest_genre["Genre"],
                f"{densest_genre['Density']:.4f}"
            )


        st.divider()


        # -------------------------------------------------
        # CONNECTIONS BY GENRE
        # -------------------------------------------------

        st.markdown(
            "#### 🔗 Connections by Genre"
        )


        connections_chart = (
            genre_comparison_df
            .sort_values(
                "Connections",
                ascending=False
            )
            .head(10)
            .set_index("Genre")[
                ["Connections"]
            ]
        )


        st.bar_chart(
            connections_chart
        )


        # -------------------------------------------------
        # DENSITY BY GENRE
        # -------------------------------------------------

        st.markdown(
            "#### 📊 Network Density by Genre"
        )


        density_chart = (
            genre_comparison_df
            .sort_values(
                "Density",
                ascending=False
            )
            .head(10)
            .set_index("Genre")[
                ["Density"]
            ]
        )


        st.bar_chart(
            density_chart
        )


        # -------------------------------------------------
        # COMPLETE TABLE
        # -------------------------------------------------

        st.markdown(
            "#### 📋 Detailed Genre Statistics"
        )


        display_genre_df = (
            genre_comparison_df
            .sort_values(
                "Connections",
                ascending=False
            )
            .copy()
        )


        display_genre_df[
            "Density"
        ] = display_genre_df[
            "Density"
        ].round(4)


        st.dataframe(
            display_genre_df,
            use_container_width=True,
            hide_index=True
        )


        # -------------------------------------------------
        # GENRE INSIGHTS
        # -------------------------------------------------

        st.markdown(
            "#### 💡 Genre Insights"
        )


        st.markdown(
            f"""
            🔹 **{largest_genre["Genre"]}** has the
            largest actor network with approximately
            **{int(largest_genre["Actors"])} actors**.

            🔹 **{most_connected_genre["Genre"]}** has the
            greatest number of collaboration connections,
            with **{int(most_connected_genre["Connections"])} connections**.

            🔹 **{densest_genre["Genre"]}** has the highest
            network density at **{densest_genre["Density"]:.4f}**.
            """
        )

    else:

        st.info(
            "No genre information is available for "
            "the current filters."
        )


# =========================================================
# HOW TO READ VISUALISATION
# =========================================================

st.divider()

with st.expander(
    "📚 How to Read This Visualisation"
):

    st.markdown(
        """
        ### 🟢 Nodes

        Each node represents an **actor**.

        ### 📏 Node Size

        Larger nodes represent actors with more
        direct collaborators.

        ### 🔗 Edges

        An edge represents a movie collaboration
        between two actors.

        ### 💪 Edge Thickness

        Thicker edges represent stronger collaborations,
        meaning the actors shared more movies.

        ### 🎨 Community Colour

        Actors belonging to the same detected
        community are given the same colour.

        ### 📍 Position

        The force-directed layout places related
        actors near each other, helping reveal
        clusters and groups.

        ### 🔎 Filtering

        Year, genre and collaboration filters allow
        users to focus on a specific part of the network.

        This helps reduce **information overload**.
        """
    )


# =========================================================
# ABOUT THE PROJECT
# =========================================================

with st.expander(
    "ℹ️ About This Project"
):

    st.markdown(
        """
        ## Movie Collaboration Explorer

        This application represents the movie industry
        as an **actor collaboration network**.

        ### Graph Model

        | Graph Element | Representation |
        |---|---|
        | Vertex / Node | Actor |
        | Edge | Two actors appeared in the same movie |
        | Edge weight | Number of shared movies |
        | Node size | Number of direct collaborators |
        | Node colour | Detected community |
        | Node position | Force-directed network layout |

        ### Main Questions

        1. How are actors connected through movies?
        2. Which actors have the most collaborators?
        3. Which actor pairs collaborate most frequently?
        4. What communities exist in the network?
        5. Which actors act as bridges between communities?
        6. How does the network change over time?
        7. How does collaboration differ across genres?

        ### Interaction

        The application supports:

        - Actor search
        - Year filtering
        - Genre filtering
        - Collaboration filtering
        - Zoom
        - Pan
        - Node dragging
        - Actor exploration
        - Ego-network exploration
        - Details-on-demand
        - Community analysis
        - Time analysis
        - Genre comparison
        """
    )


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.caption(
    "Movie Collaboration Explorer | "
    "Interactive Graph Visualisation Project"
)