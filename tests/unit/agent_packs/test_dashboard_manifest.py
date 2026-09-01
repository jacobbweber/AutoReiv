from src.application.agent_packs.schema import (
    AgentDashboardManifest,
    AgentPackManifest,
    DashboardActionItem,
    DashboardCardDefinition,
    DashboardCardType,
    DashboardStatItem,
    DashboardTableColumn,
    DashboardTableRowAction,
)


def test_dashboard_manifest_valid():
    manifest = AgentDashboardManifest(
        pack_id="gardening",
        tab_title="Garden Studio",
        icon="sprout",
        description="Hydroponics and soil garden telemetry",
        cards=[
            DashboardCardDefinition(
                id="soil_sensors",
                type=DashboardCardType.STAT_GROUP,
                title="Soil Sensors",
                width="half",
                stats=[
                    DashboardStatItem(
                        id="moisture",
                        label="Soil Moisture",
                        value="68%",
                        icon="droplets",
                        accent="emerald",
                    ),
                    DashboardStatItem(
                        id="harvest_days",
                        label="Days to Harvest",
                        value="14",
                        icon="calendar",
                    ),
                ],
            ),
            DashboardCardDefinition(
                id="quick_actions",
                type=DashboardCardType.ACTION_GROUP,
                title="Quick Actions",
                width="half",
                actions=[
                    DashboardActionItem(
                        id="water_bed_1",
                        label="Water Bed 1",
                        icon="droplet",
                        variant="primary",
                        tool="water_plants",
                        args={"bed": 1, "volume_ml": 500},
                    )
                ],
            ),
            DashboardCardDefinition(
                id="plant_roster",
                type=DashboardCardType.DATA_TABLE,
                title="Active Plant Roster",
                width="full",
                columns=[
                    DashboardTableColumn(key="name", label="Plant Name"),
                    DashboardTableColumn(key="location", label="Location"),
                    DashboardTableColumn(key="status", label="Status"),
                ],
                rows=[
                    {"name": "Roma Tomatoes", "location": "Bed 1", "status": "Healthy"},
                    {"name": "Sweet Basil", "location": "Pot A", "status": "Dry"},
                ],
                row_actions=[
                    DashboardTableRowAction(
                        id="water_row",
                        label="Water",
                        tool="water_plants",
                        arg_mapping={"bed": "location"},
                    )
                ],
            ),
            DashboardCardDefinition(
                id="journal",
                type=DashboardCardType.MARKDOWN_EDITOR,
                title="Daily Garden Journal",
                width="full",
                file_path="docs/garden_journal.md",
                content="# Summer Garden Notes\n\n- [x] Watered at 8am",
                save_tool="write_project_file",
            ),
        ],
    )

    assert manifest.pack_id == "gardening"
    assert manifest.tab_title == "Garden Studio"
    assert len(manifest.cards) == 4
    assert manifest.cards[0].type == DashboardCardType.STAT_GROUP
    assert manifest.cards[3].type == DashboardCardType.MARKDOWN_EDITOR

    # Test serialization and deserialization
    json_str = manifest.model_dump_json()
    reloaded = AgentDashboardManifest.model_validate_json(json_str)
    assert reloaded.pack_id == "gardening"
    assert len(reloaded.cards) == 4


def test_agent_pack_manifest_with_dashboard():
    pack = AgentPackManifest(
        id="gardening",
        name="Gardener",
        description="Garden specialist",
        dashboard=AgentDashboardManifest(
            pack_id="gardening",
            tab_title="Garden Studio",
            icon="sprout",
            cards=[],
        ),
    )
    assert pack.dashboard is not None
    assert pack.dashboard.tab_title == "Garden Studio"
