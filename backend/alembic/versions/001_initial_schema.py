"""Initial schema with all models

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-12-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create leagues table
    op.create_table(
        'leagues',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('sport', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_leagues_id', 'leagues', ['id'])
    op.create_index('ix_leagues_name', 'leagues', ['name'])

    # Create teams table
    op.create_table(
        'teams',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('league_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('abbreviation', sa.String(), nullable=True),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('external_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['league_id'], ['leagues.id']),
    )
    op.create_index('ix_teams_id', 'teams', ['id'])
    op.create_index('ix_teams_league_id', 'teams', ['league_id'])
    op.create_index('ix_teams_name', 'teams', ['name'])

    # Create golfers table
    op.create_table(
        'golfers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('country', sa.String(), nullable=True),
        sa.Column('external_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_golfers_id', 'golfers', ['id'])
    op.create_index('ix_golfers_name', 'golfers', ['name'])

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(), nullable=False, unique=True),
        sa.Column('username', sa.String(), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('role', sa.Enum('USER', 'LEAGUE_ADMIN', 'GLOBAL_ADMIN', name='userrole'), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'PENDING_DELETION', 'DELETED', name='accountstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('deletion_requested_at', sa.DateTime(), nullable=True),
        sa.Column('has_dismissed_onboarding', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_username', 'users', ['username'])

    # Create competitions table
    op.create_table(
        'competitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('mode', sa.Enum('DAILY_PICKS', 'FIXED_TEAMS', name='competitionmode'), nullable=False),
        sa.Column('status', sa.Enum('UPCOMING', 'ACTIVE', 'COMPLETED', name='competitionstatus'), nullable=False),
        sa.Column('league_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('display_timezone', sa.String(), nullable=False, server_default='UTC'),
        sa.Column('visibility', sa.Enum('PUBLIC', 'PRIVATE', name='visibility'), nullable=False),
        sa.Column('join_type', sa.Enum('OPEN', 'REQUIRES_APPROVAL', name='jointype'), nullable=False),
        sa.Column('max_participants', sa.Integer(), nullable=True),
        sa.Column('max_picks_per_day', sa.Integer(), nullable=True),
        sa.Column('max_teams_per_participant', sa.Integer(), nullable=True),
        sa.Column('max_golfers_per_participant', sa.Integer(), nullable=True),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('league_admin_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False, server_default='{}'),
        sa.Column('winner_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['league_id'], ['leagues.id']),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id']),
        sa.ForeignKeyConstraint(['winner_user_id'], ['users.id']),
    )
    op.create_index('ix_competitions_id', 'competitions', ['id'])
    op.create_index('ix_competitions_status', 'competitions', ['status'])
    op.create_index('ix_competitions_league_id', 'competitions', ['league_id'])
    op.create_index('ix_competitions_creator_id', 'competitions', ['creator_id'])
    op.create_index('ix_competitions_start_date', 'competitions', ['start_date'])
    op.create_index('ix_competitions_end_date', 'competitions', ['end_date'])

    # Create games table
    op.create_table(
        'games',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('competition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('external_id', sa.String(), nullable=False),
        sa.Column('home_team_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('away_team_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scheduled_start_time', sa.DateTime(), nullable=False),
        sa.Column('actual_start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('SCHEDULED', 'IN_PROGRESS', 'FINAL', 'POSTPONED', 'CANCELLED', 'NO_RESULT', name='gamestatus'), nullable=False),
        sa.Column('home_team_score', sa.Integer(), nullable=True),
        sa.Column('away_team_score', sa.Integer(), nullable=True),
        sa.Column('winner_team_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('venue_name', sa.String(), nullable=True),
        sa.Column('venue_city', sa.String(), nullable=True),
        sa.Column('api_data', postgresql.JSON(), nullable=True),
        sa.Column('score_corrected_at', sa.DateTime(), nullable=True),
        sa.Column('score_correction_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['competition_id'], ['competitions.id']),
        sa.ForeignKeyConstraint(['home_team_id'], ['teams.id']),
        sa.ForeignKeyConstraint(['away_team_id'], ['teams.id']),
        sa.ForeignKeyConstraint(['winner_team_id'], ['teams.id']),
    )
    op.create_index('ix_games_id', 'games', ['id'])
    op.create_index('ix_games_competition_id', 'games', ['competition_id'])
    op.create_index('ix_games_external_id', 'games', ['external_id'])
    op.create_index('ix_games_home_team_id', 'games', ['home_team_id'])
    op.create_index('ix_games_away_team_id', 'games', ['away_team_id'])
    op.create_index('ix_games_scheduled_start_time', 'games', ['scheduled_start_time'])
    op.create_index('ix_games_status', 'games', ['status'])
    op.create_index('ix_games_winner_team_id', 'games', ['winner_team_id'])

    # Create participants table
    op.create_table(
        'participants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('competition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('total_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_wins', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_losses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('accuracy_percentage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('current_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.Column('last_pick_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['competition_id'], ['competitions.id']),
    )
    op.create_index('ix_participants_id', 'participants', ['id'])
    op.create_index('ix_participants_user_id', 'participants', ['user_id'])
    op.create_index('ix_participants_competition_id', 'participants', ['competition_id'])
    op.create_index('ix_participants_total_points', 'participants', ['total_points'])

    # Create picks table
    op.create_table(
        'picks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('competition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('game_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('predicted_winner_team_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('locked_at', sa.DateTime(), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('points_earned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['competition_id'], ['competitions.id']),
        sa.ForeignKeyConstraint(['game_id'], ['games.id']),
        sa.ForeignKeyConstraint(['predicted_winner_team_id'], ['teams.id']),
        sa.CheckConstraint('user_id IS NOT NULL AND competition_id IS NOT NULL AND game_id IS NOT NULL'),
    )
    op.create_index('ix_picks_id', 'picks', ['id'])
    op.create_index('ix_picks_user_id', 'picks', ['user_id'])
    op.create_index('ix_picks_competition_id', 'picks', ['competition_id'])
    op.create_index('ix_picks_game_id', 'picks', ['game_id'])
    op.create_index('ix_picks_is_locked', 'picks', ['is_locked'])

    # Create fixed_team_selections table
    op.create_table(
        'fixed_team_selections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('competition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('team_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('golfer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('locked_at', sa.DateTime(), nullable=True),
        sa.Column('total_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['competition_id'], ['competitions.id']),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
        sa.ForeignKeyConstraint(['golfer_id'], ['golfers.id']),
        sa.CheckConstraint('(team_id IS NOT NULL AND golfer_id IS NULL) OR (team_id IS NULL AND golfer_id IS NOT NULL)'),
    )
    op.create_index('ix_fixed_team_selections_id', 'fixed_team_selections', ['id'])
    op.create_index('ix_fixed_team_selections_user_id', 'fixed_team_selections', ['user_id'])
    op.create_index('ix_fixed_team_selections_competition_id', 'fixed_team_selections', ['competition_id'])
    op.create_index('ix_fixed_team_selections_team_id', 'fixed_team_selections', ['team_id'])
    op.create_index('ix_fixed_team_selections_golfer_id', 'fixed_team_selections', ['golfer_id'])
    op.create_index('ix_fixed_team_selections_is_locked', 'fixed_team_selections', ['is_locked'])

    # Create join_requests table
    op.create_table(
        'join_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('competition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='joinrequeststatus'), nullable=False),
        sa.Column('reviewed_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['competition_id'], ['competitions.id']),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id']),
    )
    op.create_index('ix_join_requests_id', 'join_requests', ['id'])
    op.create_index('ix_join_requests_user_id', 'join_requests', ['user_id'])
    op.create_index('ix_join_requests_competition_id', 'join_requests', ['competition_id'])
    op.create_index('ix_join_requests_status', 'join_requests', ['status'])

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_type', sa.String(), nullable=True),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('details', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    # Create composite indexes for common queries
    op.create_index('ix_picks_user_comp_game', 'picks', ['user_id', 'competition_id', 'game_id'], unique=True)
    op.create_index('ix_participants_user_comp', 'participants', ['user_id', 'competition_id'], unique=True)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('audit_logs')
    op.drop_table('join_requests')
    op.drop_table('fixed_team_selections')
    op.drop_table('picks')
    op.drop_table('participants')
    op.drop_table('games')
    op.drop_table('competitions')
    op.drop_table('users')
    op.drop_table('golfers')
    op.drop_table('teams')
    op.drop_table('leagues')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS joinrequeststatus')
    op.execute('DROP TYPE IF EXISTS gamestatus')
    op.execute('DROP TYPE IF EXISTS jointype')
    op.execute('DROP TYPE IF EXISTS visibility')
    op.execute('DROP TYPE IF EXISTS competitionstatus')
    op.execute('DROP TYPE IF EXISTS competitionmode')
    op.execute('DROP TYPE IF EXISTS accountstatus')
    op.execute('DROP TYPE IF EXISTS userrole')
