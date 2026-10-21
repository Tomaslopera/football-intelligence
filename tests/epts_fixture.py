"""Hand-authored synthetic EPTS pair; contains no competition observations."""

from pathlib import Path
from xml.etree import ElementTree as ET


def write_epts_pair(
    directory: Path,
    *,
    speed_unit: str = "m/s",
    speeds: tuple[float, float] = (2, 3),
) -> tuple[Path, Path]:
    root = ET.Element("main")
    metadata = ET.SubElement(root, "Metadata")
    config = ET.SubElement(metadata, "GlobalConfig")
    ET.SubElement(config, "ProviderName").text = "Metrica Sports"
    ET.SubElement(config, "FrameRate").text = "25"
    global_parameters = ET.SubElement(config, "ProviderGlobalParameters")
    for name, value in (("first_half_start", "1"), ("first_half_end", "3")):
        parameter = ET.SubElement(global_parameters, "ProviderParameter")
        ET.SubElement(parameter, "Name").text = name
        ET.SubElement(parameter, "Value").text = value
    session = ET.SubElement(ET.SubElement(metadata, "Sessions"), "Session")
    parameters = ET.SubElement(session, "MatchParameters")
    score = ET.SubElement(
        parameters, "Score", idLocalTeam="home", idVisitingTeam="away"
    )
    ET.SubElement(score, "LocalTeamScore").text = "0"
    ET.SubElement(score, "VisitingTeamScore").text = "0"
    size = ET.SubElement(session, "FieldSize")
    ET.SubElement(size, "Width").text = "105"
    ET.SubElement(size, "Height").text = "68"
    teams = ET.SubElement(metadata, "Teams")
    # Deliberately reverse team order and interleave numeric slots.
    for identifier in ("away", "home"):
        team = ET.SubElement(teams, "Team", id=identifier)
        ET.SubElement(team, "Name").text = f"Synthetic {identifier}"
        provider = ET.SubElement(team, "ProviderTeamsParameters")
        param = ET.SubElement(provider, "ProviderParameter")
        ET.SubElement(param, "Name").text = "attack_direction_first_half"
        ET.SubElement(param, "Value").text = "left_to_right"
    players = ET.SubElement(metadata, "Players")
    for slot, team_id in ((1, "away"), (7, "home")):
        player = ET.SubElement(players, "Player", id=f"Track_{slot}", teamId=team_id)
        ET.SubElement(player, "Name").text = f"Track_{slot}"
        ET.SubElement(player, "ShirtNumber").text = str(slot)
        ET.SubElement(player, "ProviderPlayerParameters")
    device = ET.SubElement(ET.SubElement(metadata, "Devices"), "Device")
    sensors = ET.SubElement(device, "Sensors")
    for sensor_id, columns, unit in (
        ("position", ("x", "y"), "normalized"),
        ("speed", ("s",), speed_unit),
    ):
        sensor = ET.SubElement(sensors, "Sensor", id=sensor_id)
        ET.SubElement(sensor, "Name").text = sensor_id
        channels = ET.SubElement(sensor, "Channels")
        for column in columns:
            channel = ET.SubElement(channels, "Channel", id=column)
            ET.SubElement(channel, "Name").text = column
            ET.SubElement(channel, "Unit").text = unit
    player_channels = ET.SubElement(metadata, "PlayerChannels")
    specs = ET.SubElement(root, "DataFormatSpecifications")
    spec = ET.SubElement(
        specs, "DataFormatSpecification", startFrame="1", endFrame="3", separator=":"
    )
    ET.SubElement(spec, "StringRegister", name="frameCount")
    registers = ET.SubElement(spec, "SplitRegister", separator=";")
    for slot in (1, 7):
        register = ET.SubElement(registers, "SplitRegister", separator=",")
        for column in ("x", "y", "s"):
            channel_id = f"slot{slot}_{column}"
            ET.SubElement(
                player_channels,
                "PlayerChannel",
                id=channel_id,
                playerId=f"Track_{slot}",
                channelId=column,
            )
            ET.SubElement(register, "PlayerChannelRef", playerChannelId=channel_id)
    ball = ET.SubElement(spec, "SplitRegister", separator=",")
    for column in ("x", "y"):
        ET.SubElement(ball, "BallChannelRef", channelId=column)
    xml_path = directory / "synthetic.xml"
    txt_path = directory / "synthetic.txt"
    ET.ElementTree(root).write(xml_path)
    away_speed, home_speed = speeds
    txt_path.write_text(
        f"1:0.2,0.4,{away_speed};0.6,0.4,{home_speed}:0.5,0.4\n"
        f"2:0.21,0.4,{away_speed};,,{home_speed}:,\n"
        f"3:0.22,0.4,{away_speed};0.62,0.4,{home_speed}:0.51,0.4\n"
    )
    return xml_path, txt_path
