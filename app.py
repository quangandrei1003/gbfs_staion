import streamlit as st
import pydeck as pdk
import pandas as pd
import json

st.title("Paris Bike Share Stations Dashboard")
st.markdown(
    "<p style='font-size:32px; color:gray; font-weight:bold;'>Bike Station Utilization Map: Availability and Usage 🚲🕹️</p>",
    unsafe_allow_html=True,
)


file_path = "data/gbfs_station_paris.json"


@st.cache_data
def load_data(file_path):
    """Load and process GBFS data."""
    with open(file_path, "r") as f:
        data = json.load(f)

    if isinstance(data, dict) and "data" in data:
        if "stations" in data["data"]:
            stations_data = data["data"]["stations"]
        else:
            stations_data = data["data"]
    else:
        stations_data = data

    return pd.DataFrame(stations_data)


def ratio_to_color(ratio):
    """Convert availability ratio to red-green color scale."""
    if pd.isna(ratio):
        return [128, 128, 128]

    ratio = max(0, min(1, float(ratio)))
    r = int((1 - ratio) * 255)
    g = int(ratio * 255)
    b = 0
    return [r, g, b]


def create_map_layers(df):
    """Create map layers for docked and dockless stations."""
    layers = []
    df["is_virtual_station"] = df["is_virtual_station"].astype(bool)

    df_docked = df[df["is_virtual_station"] == False].copy()
    df_dockless = df[df["is_virtual_station"] == True].copy()

    if len(df_docked) > 0:
        df_docked["station_type"] = "Docked"

        df_docked["availability_ratio_normalized"] = df_docked[
            "availability_ratio"
        ].apply(
            lambda x: (
                x / 100.0
                if not pd.isna(x) and x > 1
                else (x if not pd.isna(x) else 0.5)
            )
        )
        df_docked["availability_display"] = df_docked["availability_ratio"].apply(
            lambda x: f"{int(x)}%" if not pd.isna(x) else "N/A"
        )
        df_docked["info_line"] = df_docked["availability_display"].apply(
            lambda x: f"Available Ratio: {x}"
        )
        colors = [
            ratio_to_color(ratio)
            for ratio in df_docked["availability_ratio_normalized"]
        ]
        df_docked["color"] = colors

        docked_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_docked,
            get_position=["longitude", "latitude"],
            get_fill_color="color",
            get_radius=25,
            pickable=True,
            auto_highlight=True,
            id="docked_stations",
        )
        layers.append(docked_layer)

    if len(df_dockless) > 0:
        df_dockless["station_type"] = "Dockless"
        df_dockless["radius"] = df_dockless["avg_num_of_available"].apply(
            lambda x: (
                25
                if not pd.isna(x) and x >= 10
                else max(8, 8 + (x if not pd.isna(x) else 0))
            )
        )
        df_dockless["bikes_display"] = df_dockless["avg_num_of_available"].apply(
            lambda x: str(int(x)) if not pd.isna(x) else "N/A"
        )
        df_dockless["info_line"] = df_dockless["bikes_display"].apply(
            lambda x: f"Available bikes: {x}"
        )
        dockless_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_dockless,
            get_position=["longitude", "latitude"],
            get_fill_color=[0, 120, 255, 180],
            get_radius="radius",
            pickable=True,
            auto_highlight=True,
            id="dockless_stations",
        )
        layers.append(dockless_layer)

    return layers, df_docked, df_dockless


try:
    df = load_data(file_path)
    if "latitude" in df.columns and "longitude" in df.columns:
        layers, df_docked, df_dockless = create_map_layers(df)

        st.sidebar.header("Filters")
        show_docked = st.sidebar.checkbox("Docked Stations", value=True)
        show_dockless = st.sidebar.checkbox("Dockless Stations", value=True)

        if layers:
            filtered_layers = []
            if show_docked and len(df_docked) > 0:
                min_ratio = float(df_docked["availability_ratio"].min())
                ratio_filter = st.sidebar.slider(
                    "Docked: Availability Ratio (%)",
                    min_value=int(min_ratio),
                    max_value=100,
                    value=(int(min_ratio), 100),
                )

                df_docked = df_docked[
                    (df_docked["availability_ratio"] >= ratio_filter[0])
                    & (df_docked["availability_ratio"] <= ratio_filter[1])
                ]

                docked_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df_docked,
                    get_position=["longitude", "latitude"],
                    get_fill_color="color",
                    get_radius=25,
                    pickable=True,
                    auto_highlight=True,
                    id="docked_stations",
                )
                filtered_layers.append(docked_layer)

            if show_dockless and len(df_dockless) > 0:
                min_bikes = int(df_dockless["avg_num_of_available"].min())
                bikes_filter = st.sidebar.slider(
                    "Dockless: Avg Available Bikes",
                    min_value=min_bikes,
                    max_value=20,
                    value=(min_bikes, 20),
                )
                df_dockless = df_dockless[
                    (df_dockless["avg_num_of_available"] >= bikes_filter[0])
                    & (df_dockless["avg_num_of_available"] <= bikes_filter[1])
                ]

                dockless_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df_dockless,
                    get_position=["longitude", "latitude"],
                    get_fill_color=[0, 120, 255, 180],
                    get_radius="radius",
                    pickable=True,
                    auto_highlight=True,
                    id="dockless_stations",
                )
                filtered_layers.append(dockless_layer)

            if filtered_layers:
                view_state = pdk.ViewState(
                    latitude=df["latitude"].mean(),
                    longitude=df["longitude"].mean(),
                    zoom=11,
                    pitch=0,
                )

                tooltip = {
                    "html": "<b>{name}</b><br/>"
                    "Type: {station_type} Station <br/>"
                    "{info_line}<br />",
                    "style": {"backgroundColor": "rgba(0,0,0,0.8)", "color": "white"},
                }

                deck = pdk.Deck(
                    layers=filtered_layers,
                    initial_view_state=view_state,
                    tooltip=tooltip,
                )
                st.pydeck_chart(deck, use_container_width=True)
                st.write("**Map Controls:**")
                st.write(
                    "• **Zoom:** Two-finger scroll or +/- • **Pan:** Click & drag or arrow keys • **Focus:** Double-click"
                )
            else:
                st.warning(
                    "Please select at least one station type to display on the map."
                )

            visible_docked = len(df_docked) if show_docked else 0
            visible_dockless = len(df_dockless) if show_dockless else 0
            visible_total = visible_docked + visible_dockless

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Stations", visible_total)
            with col2:
                st.metric("Docked Stations", f"{visible_docked}")
            with col3:
                st.metric("Dockless Stations", f"{visible_dockless}")

            st.sidebar.subheader("Legend")
            st.sidebar.write("**Docked Stations:**")
            st.sidebar.write(
                "🔴 Red = Busy (few bikes available) • 🟢 Green = Free (many bikes available"
            )
            gradient_html = """
                <div style="display: flex; align-items: center; margin: 10px 0;">
                    <span style="margin-right: 10px; font-size: 12px;">0%</span>
                    <div style="
                        width: 200px; 
                        height: 20px; 
                        background: linear-gradient(to right, 
                            rgb(255,0,0) 0%, 
                            rgb(255,128,0) 25%, 
                            rgb(255,255,0) 50%, 
                            rgb(128,255,0) 75%, 
                            rgb(0,255,0) 100%
                        );
                        border: 1px solid #ccc;
                        border-radius: 3px;
                    "></div>
                    <span style="margin-left: 10px; font-size: 12px;">100%</span>
                </div>
                """
            st.sidebar.markdown(gradient_html, unsafe_allow_html=True)
            st.sidebar.write("**🔵 Dockless Stations:**")
            st.sidebar.write("• Blue color • Size varies by available bikes")

        else:
            st.error("No valid station data found.")
    else:
        st.error("Required columns (latitude, longitude) not found in data.")

except FileNotFoundError:
    st.error(f"File '{file_path}' not found.")
except json.JSONDecodeError:
    st.error("Invalid JSON file format.")
except Exception as e:
    st.error(f"An error occurred: {str(e)}")
