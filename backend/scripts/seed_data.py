"""
Seed data script for United Degenerates League

This script populates the database with:
- Leagues (NFL, NBA, MLB, NHL, NCAA)
- Teams for each league
- Sample users
- Sample competitions
- Games for testing

Run with: python -m scripts.seed_data
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session
from app.models.league import League, Team
from app.models.user import User, UserRole, AccountStatus
from app.models.competition import Competition, CompetitionMode, CompetitionStatus, Visibility, JoinType
from app.models.game import Game, GameStatus
from app.models.participant import Participant
from app.core.security import get_password_hash


# NFL Teams
NFL_TEAMS = [
    ("Arizona Cardinals", "Arizona", "ARI"),
    ("Atlanta Falcons", "Atlanta", "ATL"),
    ("Baltimore Ravens", "Baltimore", "BAL"),
    ("Buffalo Bills", "Buffalo", "BUF"),
    ("Carolina Panthers", "Carolina", "CAR"),
    ("Chicago Bears", "Chicago", "CHI"),
    ("Cincinnati Bengals", "Cincinnati", "CIN"),
    ("Cleveland Browns", "Cleveland", "CLE"),
    ("Dallas Cowboys", "Dallas", "DAL"),
    ("Denver Broncos", "Denver", "DEN"),
    ("Detroit Lions", "Detroit", "DET"),
    ("Green Bay Packers", "Green Bay", "GB"),
    ("Houston Texans", "Houston", "HOU"),
    ("Indianapolis Colts", "Indianapolis", "IND"),
    ("Jacksonville Jaguars", "Jacksonville", "JAX"),
    ("Kansas City Chiefs", "Kansas City", "KC"),
    ("Las Vegas Raiders", "Las Vegas", "LV"),
    ("Los Angeles Chargers", "Los Angeles", "LAC"),
    ("Los Angeles Rams", "Los Angeles", "LAR"),
    ("Miami Dolphins", "Miami", "MIA"),
    ("Minnesota Vikings", "Minnesota", "MIN"),
    ("New England Patriots", "New England", "NE"),
    ("New Orleans Saints", "New Orleans", "NO"),
    ("New York Giants", "New York", "NYG"),
    ("New York Jets", "New York", "NYJ"),
    ("Philadelphia Eagles", "Philadelphia", "PHI"),
    ("Pittsburgh Steelers", "Pittsburgh", "PIT"),
    ("San Francisco 49ers", "San Francisco", "SF"),
    ("Seattle Seahawks", "Seattle", "SEA"),
    ("Tampa Bay Buccaneers", "Tampa Bay", "TB"),
    ("Tennessee Titans", "Tennessee", "TEN"),
    ("Washington Commanders", "Washington", "WAS"),
]

# NBA Teams
NBA_TEAMS = [
    ("Atlanta Hawks", "Atlanta", "ATL"),
    ("Boston Celtics", "Boston", "BOS"),
    ("Brooklyn Nets", "Brooklyn", "BKN"),
    ("Charlotte Hornets", "Charlotte", "CHA"),
    ("Chicago Bulls", "Chicago", "CHI"),
    ("Cleveland Cavaliers", "Cleveland", "CLE"),
    ("Dallas Mavericks", "Dallas", "DAL"),
    ("Denver Nuggets", "Denver", "DEN"),
    ("Detroit Pistons", "Detroit", "DET"),
    ("Golden State Warriors", "Golden State", "GSW"),
    ("Houston Rockets", "Houston", "HOU"),
    ("Indiana Pacers", "Indiana", "IND"),
    ("Los Angeles Clippers", "Los Angeles", "LAC"),
    ("Los Angeles Lakers", "Los Angeles", "LAL"),
    ("Memphis Grizzlies", "Memphis", "MEM"),
    ("Miami Heat", "Miami", "MIA"),
    ("Milwaukee Bucks", "Milwaukee", "MIL"),
    ("Minnesota Timberwolves", "Minnesota", "MIN"),
    ("New Orleans Pelicans", "New Orleans", "NOP"),
    ("New York Knicks", "New York", "NYK"),
    ("Oklahoma City Thunder", "Oklahoma City", "OKC"),
    ("Orlando Magic", "Orlando", "ORL"),
    ("Philadelphia 76ers", "Philadelphia", "PHI"),
    ("Phoenix Suns", "Phoenix", "PHX"),
    ("Portland Trail Blazers", "Portland", "POR"),
    ("Sacramento Kings", "Sacramento", "SAC"),
    ("San Antonio Spurs", "San Antonio", "SAS"),
    ("Toronto Raptors", "Toronto", "TOR"),
    ("Utah Jazz", "Utah", "UTA"),
    ("Washington Wizards", "Washington", "WAS"),
]


async def create_leagues_and_teams(db: AsyncSession):
    """Create leagues and their teams"""
    print("Creating leagues and teams...")

    # Create NFL League
    nfl = League(
        id=uuid.uuid4(),
        name="NFL",
        sport="Football",
    )
    db.add(nfl)
    await db.flush()

    print(f"Created NFL league: {nfl.id}")

    # Create NFL Teams
    nfl_team_objs = []
    for name, city, abbr in NFL_TEAMS:
        team = Team(
            id=uuid.uuid4(),
            league_id=nfl.id,
            name=name,
            city=city,
            abbreviation=abbr,
            external_id=f"nfl_{abbr.lower()}",
        )
        db.add(team)
        nfl_team_objs.append(team)

    print(f"Created {len(NFL_TEAMS)} NFL teams")

    # Create NBA League
    nba = League(
        id=uuid.uuid4(),
        name="NBA",
        sport="Basketball",
    )
    db.add(nba)
    await db.flush()

    print(f"Created NBA league: {nba.id}")

    # Create NBA Teams
    nba_team_objs = []
    for name, city, abbr in NBA_TEAMS:
        team = Team(
            id=uuid.uuid4(),
            league_id=nba.id,
            name=name,
            city=city,
            abbreviation=abbr,
            external_id=f"nba_{abbr.lower()}",
        )
        db.add(team)
        nba_team_objs.append(team)

    print(f"Created {len(NBA_TEAMS)} NBA teams")

    await db.commit()

    return {
        "nfl": {"league": nfl, "teams": nfl_team_objs},
        "nba": {"league": nba, "teams": nba_team_objs},
    }


async def create_sample_users(db: AsyncSession):
    """Create sample users for testing"""
    print("\nCreating sample users...")

    users = []

    # Admin user
    admin = User(
        id=uuid.uuid4(),
        email="admin@udl.com",
        username="admin",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.GLOBAL_ADMIN,
        status=AccountStatus.ACTIVE,
    )
    db.add(admin)
    users.append(admin)
    print(f"Created admin user: admin@udl.com / admin123")

    # Regular test users
    test_users = [
        ("test1@udl.com", "TestUser1", "password123"),
        ("test2@udl.com", "TestUser2", "password123"),
        ("test3@udl.com", "TestUser3", "password123"),
        ("test4@udl.com", "TestUser4", "password123"),
        ("test5@udl.com", "TestUser5", "password123"),
    ]

    for email, username, password in test_users:
        user = User(
            id=uuid.uuid4(),
            email=email,
            username=username,
            hashed_password=get_password_hash(password),
            role=UserRole.USER,
            status=AccountStatus.ACTIVE,
        )
        db.add(user)
        users.append(user)
        print(f"Created test user: {email} / {password}")

    await db.commit()

    return users


async def create_sample_competitions(db: AsyncSession, leagues_data, users):
    """Create sample competitions with games"""
    print("\nCreating sample competitions...")

    admin = users[0]
    nfl_data = leagues_data["nfl"]
    nba_data = leagues_data["nba"]

    competitions = []

    # NFL Daily Picks Competition (Active)
    nfl_comp = Competition(
        id=uuid.uuid4(),
        name="NFL Week 15 Picks",
        description="Pick winners for NFL Week 15 games. 1 point per correct pick!",
        mode=CompetitionMode.DAILY_PICKS,
        status=CompetitionStatus.ACTIVE,
        league_id=nfl_data["league"].id,
        start_date=datetime.utcnow() - timedelta(days=2),
        end_date=datetime.utcnow() + timedelta(days=5),
        display_timezone="America/New_York",
        visibility=Visibility.PUBLIC,
        join_type=JoinType.OPEN,
        max_participants=None,
        max_picks_per_day=10,
        creator_id=admin.id,
        league_admin_ids=[str(admin.id)],
    )
    db.add(nfl_comp)
    competitions.append(nfl_comp)
    await db.flush()

    print(f"Created NFL competition: {nfl_comp.name}")

    # Add participants (all test users)
    for user in users:
        participant = Participant(
            id=uuid.uuid4(),
            user_id=user.id,
            competition_id=nfl_comp.id,
        )
        db.add(participant)

    print(f"Added {len(users)} participants to NFL competition")

    # Create NFL games for next 3 days
    nfl_teams = nfl_data["teams"]
    games_created = 0

    # Today's games
    today = datetime.utcnow().replace(hour=13, minute=0, second=0, microsecond=0)
    for i in range(0, 8, 2):
        if i + 1 < len(nfl_teams):
            game = Game(
                id=uuid.uuid4(),
                competition_id=nfl_comp.id,
                external_id=f"nfl_game_{games_created}",
                home_team_id=nfl_teams[i].id,
                away_team_id=nfl_teams[i + 1].id,
                scheduled_start_time=today + timedelta(hours=i * 3),
                status=GameStatus.SCHEDULED,
                venue_name=f"{nfl_teams[i].city} Stadium",
                venue_city=nfl_teams[i].city,
            )
            db.add(game)
            games_created += 1

    # Tomorrow's games
    tomorrow = today + timedelta(days=1)
    for i in range(8, 16, 2):
        if i + 1 < len(nfl_teams):
            game = Game(
                id=uuid.uuid4(),
                competition_id=nfl_comp.id,
                external_id=f"nfl_game_{games_created}",
                home_team_id=nfl_teams[i].id,
                away_team_id=nfl_teams[i + 1].id,
                scheduled_start_time=tomorrow + timedelta(hours=(i - 8) * 3),
                status=GameStatus.SCHEDULED,
                venue_name=f"{nfl_teams[i].city} Stadium",
                venue_city=nfl_teams[i].city,
            )
            db.add(game)
            games_created += 1

    print(f"Created {games_created} NFL games")

    # NBA Daily Picks Competition (Upcoming)
    nba_comp = Competition(
        id=uuid.uuid4(),
        name="NBA December Championship",
        description="Daily picks for NBA games throughout December. May the best predictor win!",
        mode=CompetitionMode.DAILY_PICKS,
        status=CompetitionStatus.UPCOMING,
        league_id=nba_data["league"].id,
        start_date=datetime.utcnow() + timedelta(days=1),
        end_date=datetime.utcnow() + timedelta(days=30),
        display_timezone="America/Los_Angeles",
        visibility=Visibility.PUBLIC,
        join_type=JoinType.OPEN,
        max_participants=50,
        max_picks_per_day=15,
        creator_id=admin.id,
        league_admin_ids=[str(admin.id)],
    )
    db.add(nba_comp)
    competitions.append(nba_comp)
    await db.flush()

    print(f"Created NBA competition: {nba_comp.name}")

    # Add first 3 users as participants
    for user in users[:3]:
        participant = Participant(
            id=uuid.uuid4(),
            user_id=user.id,
            competition_id=nba_comp.id,
        )
        db.add(participant)

    print(f"Added 3 participants to NBA competition")

    # Create NBA games
    nba_teams = nba_data["teams"]
    nba_games = 0

    # Games starting tomorrow
    start_time = datetime.utcnow() + timedelta(days=1)
    start_time = start_time.replace(hour=19, minute=0, second=0, microsecond=0)

    for i in range(0, 12, 2):
        if i + 1 < len(nba_teams):
            game = Game(
                id=uuid.uuid4(),
                competition_id=nba_comp.id,
                external_id=f"nba_game_{nba_games}",
                home_team_id=nba_teams[i].id,
                away_team_id=nba_teams[i + 1].id,
                scheduled_start_time=start_time + timedelta(hours=(i // 2) * 3),
                status=GameStatus.SCHEDULED,
                venue_name=f"{nba_teams[i].city} Arena",
                venue_city=nba_teams[i].city,
            )
            db.add(game)
            nba_games += 1

    print(f"Created {nba_games} NBA games")

    # NFL Fixed Teams Competition (Upcoming)
    nfl_fixed = Competition(
        id=uuid.uuid4(),
        name="NFL Playoff Fixed Teams",
        description="Select 3 teams at the start. Earn points based on their wins throughout the playoffs!",
        mode=CompetitionMode.FIXED_TEAMS,
        status=CompetitionStatus.UPCOMING,
        league_id=nfl_data["league"].id,
        start_date=datetime.utcnow() + timedelta(days=7),
        end_date=datetime.utcnow() + timedelta(days=60),
        display_timezone="America/New_York",
        visibility=Visibility.PUBLIC,
        join_type=JoinType.REQUIRES_APPROVAL,
        max_participants=20,
        max_teams_per_participant=3,
        creator_id=admin.id,
        league_admin_ids=[str(admin.id)],
    )
    db.add(nfl_fixed)
    competitions.append(nfl_fixed)

    print(f"Created NFL Fixed Teams competition: {nfl_fixed.name}")

    await db.commit()

    return competitions


async def main():
    """Main seed function"""
    print("=" * 60)
    print("UNITED DEGENERATES LEAGUE - DATABASE SEED")
    print("=" * 60)

    async with async_session() as db:
        try:
            # Create leagues and teams
            leagues_data = await create_leagues_and_teams(db)

            # Create sample users
            users = await create_sample_users(db)

            # Create competitions and games
            competitions = await create_sample_competitions(db, leagues_data, users)

            print("\n" + "=" * 60)
            print("SEED COMPLETE!")
            print("=" * 60)
            print("\nDatabase seeded with:")
            print(f"  - 2 Leagues (NFL, NBA)")
            print(f"  - {len(NFL_TEAMS)} NFL teams")
            print(f"  - {len(NBA_TEAMS)} NBA teams")
            print(f"  - {len(users)} users")
            print(f"  - {len(competitions)} competitions")
            print(f"  - Multiple games for testing")

            print("\n" + "=" * 60)
            print("TEST CREDENTIALS")
            print("=" * 60)
            print("\nAdmin Account:")
            print("  Email: admin@udl.com")
            print("  Password: admin123")
            print("\nTest Users:")
            print("  Email: test1@udl.com (through test5@udl.com)")
            print("  Password: password123")

            print("\n" + "=" * 60)
            print("NEXT STEPS")
            print("=" * 60)
            print("\n1. Start the backend:")
            print("   cd backend && uvicorn app.main:app --reload")
            print("\n2. Start the frontend:")
            print("   cd frontend && npm run dev")
            print("\n3. Login and start competing!")
            print("\n" + "=" * 60)

        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(main())
