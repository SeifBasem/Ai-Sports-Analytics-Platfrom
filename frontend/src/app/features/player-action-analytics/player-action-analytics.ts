import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { JobStatisticsApiService } from '../../services/job-statistics-api.service';
import { ProcessingJobApiResponse } from '../../models/api.model';

interface ActionResult {
  action: string;
  confidence: number;
  start_frame: number;
  end_frame: number;
  start_time: number;
  end_time: number;
  sourceVideo?: string;
}

interface VideoResult {
  name: string;
  totalActions: number;
  videoDuration: number;
  annotatedVideoUrl: string | null;
  actions: ActionResult[];
}

interface ActionStat {
  label: string;
  count: number;
  icon: string;
}

interface ActionSegmentsPayload {
  actions?: ActionResult[];
  total_actions?: number;
  video_duration?: number;
}

interface PassingStyle {
  short_pass_count: number;
  long_pass_count: number;
  total_passes: number;
  short_pass_ratio: number;
  long_pass_ratio: number;
  passing_profile: string;
  explanation: string;
}

interface AttackingThreat {
  score: number;
  components: Record<string, number>;
  explanation: string;
}

interface DisciplineRisk {
  foul_count: number;
  discipline_risk_score: number;
  risk_level: string;
  warning?: string | null;
}

interface SetPieceSummary {
  corner: number;
  freekick: number;
  penalty: number;
  'throw-in': number;
  goalkick: number;
  set_piece_count: number;
  set_piece_ratio: number;
  explanation: string;
}

interface PlayerStyleProfile {
  main_style: string;
  secondary_styles: string[];
  passing_profile: string;
  discipline_risk: string;
  suitable_team_styles: string[];
  explanation: string;
  limitations_note: string;
}

interface SuitableTeamStyles {
  recommended_team_styles: string[];
  reason: string;
}

interface TeamStyleGroup {
  label: string;
  title: string;
  styles: string[];
  tone: 'main' | 'supporting' | 'risk';
}

interface ProfileReliability {
  profile_reliability: string;
  reason: string;
}

interface PlayerActionReviewPayload {
  action_counter: Record<string, number>;
  analysis: {
    passing_style: PassingStyle;
    estimated_attacking_threat: AttackingThreat;
    discipline_risk: DisciplineRisk;
    set_piece_summary: SetPieceSummary;
    estimated_player_playing_style_profile: PlayerStyleProfile;
    suitable_team_styles: SuitableTeamStyles;
    profile_reliability: ProfileReliability;
  };
}

interface PlayerActionSessionMetadata {
  uploadBatchId?: string;
  uploadBatchTitle?: string;
  uploadBatchVideoCount?: string;
  uploadBatchIndex?: string;
  playerName?: string;
}

interface PlayerActionSession {
  id: string;
  title: string;
  batchId?: string;
  jobs: ProcessingJobApiResponse[];
  primaryJob: ProcessingJobApiResponse;
}

@Component({
  selector: 'app-player-action-analytics',
  standalone: false,
  templateUrl: './player-action-analytics.html',
  styleUrl: './player-action-analytics.scss',
})
export class PlayerActionAnalytics implements OnInit {
  hasData = false;

  allActions: ActionResult[] = [];
  totalActions = 0;
  totalDuration = 0;
  videosProcessed = 0;
  videoResults: VideoResult[] = [];
  actionStats: ActionStat[] = [];
  playerReview: PlayerActionReviewPayload | null = null;
  historyJobs: ProcessingJobApiResponse[] = [];
  historySessions: PlayerActionSession[] = [];
  selectedHistoryJobId = '';
  selectedHistoryTitle = '';
  loadingHistory = false;

  readonly actionOrder = [
    'corner',
    'foul',
    'freekick',
    'goalkick',
    'longpass',
    'ontarget',
    'penalty',
    'shortpass',
    'substitution',
    'throw-in',
  ];

  readonly actionIcons: Record<string, string> = {
    'corner': 'C',
    'foul': 'F',
    'freekick': 'FK',
    'goalkick': 'GK',
    'longpass': 'LP',
    'ontarget': 'OT',
    'penalty': 'P',
    'shortpass': 'SP',
    'substitution': 'S',
    'throw-in': 'TI',
  };

  readonly actionColors: Record<string, string> = {
    'corner': '#f97316',
    'foul': '#ef4444',
    'freekick': '#14b8a6',
    'goalkick': '#3b82f6',
    'longpass': '#8b5cf6',
    'ontarget': '#ec4899',
    'penalty': '#eab308',
    'shortpass': '#6366f1',
    'substitution': '#10b981',
    'throw-in': '#06b6d4',
  };

  private readonly styleSummaries: Record<string, string> = {
    'Possession Player': 'Best when the team wants short combinations, tempo control, and clean circulation.',
    'Direct Playmaker': 'Best when the team wants early forward passes, switches, and fast progression.',
    'Attacking Threat Player': 'Adds final-third presence through shots, chance creation, and attacking actions.',
    'Set-Piece Specialist': 'Adds value on corners, free kicks, penalties, and rehearsed dead-ball moments.',
    'Physical / Aggressive Player': 'Useful for pressure and duels, but discipline risk needs a clear role structure.',
    'Balanced Player': 'Can support multiple tactical plans without one action type dominating the profile.'
  };

  private readonly teamStylesByProfile: Record<string, string[]> = {
    'Possession Player': [
      'Possession-dominant build-up',
      'Short-combination midfield',
      'Patient positional play',
      'Control-first game model'
    ],
    'Direct Playmaker': [
      'Direct progression',
      'Counter-attacking transitions',
      'Early balls behind the back line',
      'Vertical switch-of-play systems'
    ],
    'Attacking Threat Player': [
      'Chance-heavy attacking sides',
      'High final-third pressure',
      'Forward rotations around the box',
      'Teams needing shot volume'
    ],
    'Set-Piece Specialist': [
      'Set-piece-focused teams',
      'Aerial-target systems',
      'Corner and free-kick chance creation',
      'Dead-ball specialist roles'
    ],
    'Physical / Aggressive Player': [
      'High-pressing defensive blocks',
      'Duel-heavy midfield roles',
      'Man-oriented pressure systems',
      'Compact defensive teams'
    ],
    'Balanced Player': [
      'Flexible tactical systems',
      'Hybrid midfield roles',
      'Teams that change tempo often',
      'Utility roles across phases'
    ]
  };

  constructor(
    private jobStatistics: JobStatisticsApiService,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.loadHistoryJobs();
    this.route.queryParamMap.subscribe((params) => {
      const jobId = params.get('jobId') ?? '';
      const batchId = params.get('batchId') ?? '';
      this.selectedHistoryJobId = batchId || jobId;
      this.loadStats(jobId || undefined, batchId || undefined);
    });
  }

  loadStats(processingJobId?: string, batchId?: string): void {
    if (batchId) {
      this.loadStatsFromBatch(batchId);
      return;
    }

    if (processingJobId) {
      this.loadStatsFromHistory(processingJobId);
      return;
    }

    forkJoin({
      segments: this.jobStatistics.getAllByType<ActionSegmentsPayload>('action_segments'),
      reviews: this.jobStatistics.getAllByType<PlayerActionReviewPayload>('player_action_review')
    }).subscribe({
      next: ({ segments, reviews }) => {
        this.applyLoadedStats(segments, this.mergeReviews(reviews));
      },
      error: () => {
        this.clearStats();
      }
    });
  }

  loadHistoryJobs(): void {
    this.loadingHistory = true;
    this.jobStatistics.getCompletedJobs('ActionRecognition').subscribe({
      next: (jobs) => {
        this.historyJobs = jobs;
        this.historySessions = this.buildSessions(jobs);
        this.loadingHistory = false;
        if (this.selectedHistoryJobId) {
          this.selectedHistoryTitle = this.sessionLabel(
            this.historySessions.find((session) => session.id === this.selectedHistoryJobId) ?? null
          );
        }
      },
      error: () => {
        this.loadingHistory = false;
      }
    });
  }

  onHistorySelect(jobId: string): void {
    this.selectedHistoryJobId = jobId;
    const session = this.historySessions.find((item) => item.id === jobId);
    if (session?.batchId) {
      this.loadStats(undefined, session.batchId);
      return;
    }

    this.loadStats(jobId || undefined);
  }

  jobLabel(job: ProcessingJobApiResponse | null): string {
    if (!job) return 'Selected analysis';
    const title = job.videoTitle || `Analysis ${job.id.substring(0, 8)}`;
    const date = job.completedAt || job.createdAt;
    return `${title} - ${new Date(date).toLocaleString()}`;
  }

  sessionLabel(session: PlayerActionSession | null): string {
    if (!session) return 'Selected analysis';
    const date = session.primaryJob.completedAt || session.primaryJob.createdAt;
    return `${session.title} - ${new Date(date).toLocaleString()}`;
  }

  private loadStatsFromHistory(processingJobId: string): void {
    forkJoin({
      segment: this.jobStatistics.getLatestByJobAndType<ActionSegmentsPayload>(processingJobId, 'action_segments'),
      review: this.jobStatistics.getLatestByJobAndType<PlayerActionReviewPayload>(processingJobId, 'player_action_review')
    }).subscribe({
      next: ({ segment, review }) => {
        this.selectedHistoryTitle = this.jobLabel(
          this.historyJobs.find((job) => job.id === processingJobId) ?? null
        );

        if (!segment?.actions?.length && !this.hasReviewCounts(review)) {
          this.clearStats();
          return;
        }

        this.applyLoadedStats(
          segment ? [segment] : [],
          review,
          this.selectedHistoryTitle || `Analysis ${processingJobId.substring(0, 8)}`
        );
      },
      error: () => {
        this.clearStats();
      }
    });
  }

  private loadStatsFromBatch(batchId: string): void {
    const jobsSource = this.historyJobs.length
      ? of(this.historyJobs)
      : this.jobStatistics.getCompletedJobs('ActionRecognition');

    jobsSource.subscribe({
      next: (jobs) => {
        this.historyJobs = jobs;
        this.historySessions = this.buildSessions(jobs);

        const session = this.historySessions.find((item) => item.batchId === batchId || item.id === batchId);
        if (!session) {
          this.clearStats();
          return;
        }

        this.selectedHistoryTitle = this.sessionLabel(session);
        const requests = session.jobs.map((job) => forkJoin({
          segment: this.jobStatistics.getLatestByJobAndType<ActionSegmentsPayload>(job.id, 'action_segments'),
          review: this.jobStatistics.getLatestByJobAndType<PlayerActionReviewPayload>(job.id, 'player_action_review')
        }));

        forkJoin(requests).subscribe({
          next: (rows) => {
            const segments = rows.map((row) => row.segment).filter((row): row is ActionSegmentsPayload => !!row);
            const reviews = rows.map((row) => row.review).filter((row): row is PlayerActionReviewPayload => !!row);

            if (!segments.some((segment) => segment.actions?.length) && !reviews.some((review) => this.hasReviewCounts(review))) {
              this.clearStats();
              return;
            }

            this.applyLoadedStats(
              segments,
              this.mergeReviews(reviews),
              undefined,
              session.jobs.map((job) => job.videoTitle || this.parseMetadata(job).uploadBatchTitle || `Clip ${job.id.substring(0, 8)}`)
            );
          },
          error: () => this.clearStats()
        });
      },
      error: () => this.clearStats()
    });
  }

  private applyLoadedStats(
    segmentRows: ActionSegmentsPayload[],
    review: PlayerActionReviewPayload | null,
    singleAnalysisName?: string,
    analysisNames?: string[]
  ): void {
    this.videoResults = segmentRows.map((row, index) => {
      const name = analysisNames?.[index] ?? singleAnalysisName ?? `Analysis ${index + 1}`;
      return {
        name,
        totalActions: row.total_actions ?? row.actions?.length ?? 0,
        videoDuration: row.video_duration ?? 0,
        annotatedVideoUrl: null,
        actions: row.actions ?? []
      };
    });

    this.allActions = this.videoResults.flatMap((result) =>
      result.actions.map((action) => ({ ...action, sourceVideo: result.name }))
    );

    this.playerReview = review ?? this.buildReviewFromActions(this.allActions);
    const reviewTotal = this.reviewActionTotal(this.playerReview);

    this.totalActions = reviewTotal || this.allActions.length;
    this.totalDuration = this.videoResults.reduce((sum, result) => sum + result.videoDuration, 0);
    this.videosProcessed = Math.max(this.videoResults.length, this.hasReviewCounts(this.playerReview) ? 1 : 0);
    this.computeActionStats();
    this.hasData = this.totalActions > 0 || this.actionStats.length > 0;
  }

  private buildSessions(jobs: ProcessingJobApiResponse[]): PlayerActionSession[] {
    const groups = new Map<string, ProcessingJobApiResponse[]>();
    for (const job of jobs) {
      const metadata = this.parseMetadata(job);
      const groupId = metadata.uploadBatchId || job.id;
      const group = groups.get(groupId) ?? [];
      group.push(job);
      groups.set(groupId, group);
    }

    return Array.from(groups.entries())
      .map(([id, groupJobs]) => {
        const sorted = [...groupJobs].sort((a, b) => this.dateMs(b.completedAt || b.updatedAt) - this.dateMs(a.completedAt || a.updatedAt));
        const primaryJob = sorted[0];
        const metadata = this.parseMetadata(primaryJob);
        return {
          id,
          title: metadata.uploadBatchTitle || this.batchFallbackTitle(primaryJob, sorted),
          batchId: metadata.uploadBatchId,
          jobs: sorted,
          primaryJob
        };
      })
      .sort((a, b) => this.dateMs(b.primaryJob.completedAt || b.primaryJob.updatedAt) - this.dateMs(a.primaryJob.completedAt || a.primaryJob.updatedAt));
  }

  private batchFallbackTitle(job: ProcessingJobApiResponse, jobs: ProcessingJobApiResponse[]): string {
    const metadata = this.parseMetadata(job);
    if (metadata.playerName) {
      return `${metadata.playerName} - ${jobs.length} clip${jobs.length === 1 ? '' : 's'}`;
    }
    return job.videoTitle || `Player review - ${jobs.length} clip${jobs.length === 1 ? '' : 's'}`;
  }

  private parseMetadata(job: ProcessingJobApiResponse): PlayerActionSessionMetadata {
    if (!job.metadataJson) return {};
    try {
      return JSON.parse(job.metadataJson) as PlayerActionSessionMetadata;
    } catch {
      return {};
    }
  }

  private dateMs(value?: string | null): number {
    return value ? new Date(value).getTime() : 0;
  }

  private mergeReviews(reviews: PlayerActionReviewPayload[]): PlayerActionReviewPayload | null {
    const validReviews = reviews.filter((review) => this.hasReviewCounts(review));
    if (validReviews.length === 0) return null;

    const counts = Object.fromEntries(this.actionOrder.map((action) => [action, 0])) as Record<string, number>;
    for (const review of validReviews) {
      for (const action of this.actionOrder) {
        counts[action] += Number(review.action_counter?.[action] ?? 0);
      }
    }

    return this.buildReviewFromCounter(counts);
  }

  private hasReviewCounts(review: PlayerActionReviewPayload | null): boolean {
    return this.reviewActionTotal(review) > 0;
  }

  private reviewActionTotal(review: PlayerActionReviewPayload | null): number {
    if (!review?.action_counter) return 0;
    return this.actionOrder.reduce((sum, action) => sum + Number(review.action_counter[action] ?? 0), 0);
  }

  private buildReviewFromActions(actions: ActionResult[]): PlayerActionReviewPayload | null {
    if (!actions.length) return null;

    const counts = Object.fromEntries(this.actionOrder.map((action) => [action, 0])) as Record<string, number>;
    for (const action of actions) {
      const key = this.actionKey(action.action);
      if (key in counts) {
        counts[key]++;
      }
    }

    const confidenceSum = actions.reduce((sum, action) => sum + this.normalizeConfidence(action.confidence), 0);
    return this.buildReviewFromCounter(counts, confidenceSum / actions.length);
  }

  private buildReviewFromCounter(
    counts: Record<string, number>,
    averageConfidence = 0
  ): PlayerActionReviewPayload {
    const totalClips = this.actionOrder.reduce((sum, action) => sum + Number(counts[action] ?? 0), 0);
    const shortCount = Number(counts['shortpass'] ?? 0);
    const longCount = Number(counts['longpass'] ?? 0);
    const totalPasses = shortCount + longCount;
    const shortRatio = totalPasses ? shortCount / totalPasses : 0;
    const longRatio = totalPasses ? longCount / totalPasses : 0;

    const passingStyle = this.buildPassingStyle(shortCount, longCount, totalPasses, shortRatio, longRatio);
    const disciplineRisk = this.buildDisciplineRisk(Number(counts['foul'] ?? 0));
    const playerProfile = this.buildPlayerProfile(counts, passingStyle, disciplineRisk, totalClips);
    const teamStyles = this.buildSuitableTeamStyles(playerProfile);

    return {
      action_counter: { ...counts },
      analysis: {
        passing_style: passingStyle,
        estimated_attacking_threat: this.buildAttackingThreat(counts),
        discipline_risk: disciplineRisk,
        set_piece_summary: this.buildSetPieceSummary(counts, totalClips),
        estimated_player_playing_style_profile: playerProfile,
        suitable_team_styles: teamStyles,
        profile_reliability: this.buildProfileReliability(totalClips, averageConfidence)
      }
    };
  }

  private buildPassingStyle(
    shortCount: number,
    longCount: number,
    totalPasses: number,
    shortRatio: number,
    longRatio: number
  ): PassingStyle {
    let passingProfile = 'Not enough passing data';
    let explanation = 'No short pass or long pass clips were detected.';

    if (totalPasses > 0 && shortRatio >= 0.7) {
      passingProfile = 'Short-passing oriented';
      explanation = 'The player relies more on short passes than long passes.';
    } else if (totalPasses > 0 && longRatio >= 0.45) {
      passingProfile = 'Direct-passing oriented';
      explanation = 'The player uses long passes frequently, suggesting a direct passing style.';
    } else if (totalPasses > 0) {
      passingProfile = 'Balanced passing profile';
      explanation = 'The player shows a balanced use of short and long passes.';
    }

    return {
      short_pass_count: shortCount,
      long_pass_count: longCount,
      total_passes: totalPasses,
      short_pass_ratio: this.roundRatio(shortRatio),
      long_pass_ratio: this.roundRatio(longRatio),
      passing_profile: passingProfile,
      explanation
    };
  }

  private buildAttackingThreat(counts: Record<string, number>): AttackingThreat {
    const ontarget = Number(counts['ontarget'] ?? 0);
    const penalty = Number(counts['penalty'] ?? 0);
    const freekick = Number(counts['freekick'] ?? 0);
    const corner = Number(counts['corner'] ?? 0);
    const longpass = Number(counts['longpass'] ?? 0);

    return {
      score: this.roundRatio((ontarget * 4) + (penalty * 5) + (freekick * 2) + (corner * 2) + (longpass * 0.5)),
      components: { ontarget, penalty, freekick, corner, longpass },
      explanation: 'The player shows attacking involvement through shots on target, free kicks, corners, penalties, or long progressive passes. This is an estimated clip-based score only.'
    };
  }

  private buildDisciplineRisk(foulCount: number): DisciplineRisk {
    const riskLevel = foulCount <= 10 ? 'Low' : foulCount <= 15 ? 'Medium' : 'High';
    return {
      foul_count: foulCount,
      discipline_risk_score: foulCount * 2,
      risk_level: riskLevel,
      warning: riskLevel === 'High'
        ? 'High foul frequency may increase the risk of conceding dangerous free kicks or receiving cards.'
        : null
    };
  }

  private buildSetPieceSummary(counts: Record<string, number>, totalClips: number): SetPieceSummary {
    const corner = Number(counts['corner'] ?? 0);
    const freekick = Number(counts['freekick'] ?? 0);
    const penalty = Number(counts['penalty'] ?? 0);
    const throwIn = Number(counts['throw-in'] ?? 0);
    const goalkick = Number(counts['goalkick'] ?? 0);
    const setPieceCount = corner + freekick + penalty + throwIn + goalkick;

    return {
      corner,
      freekick,
      penalty,
      'throw-in': throwIn,
      goalkick,
      set_piece_count: setPieceCount,
      set_piece_ratio: totalClips ? this.roundRatio(setPieceCount / totalClips) : 0,
      explanation: 'This shows how often the uploaded clips contain set-piece or restart situations.'
    };
  }

  private buildPlayerProfile(
    counts: Record<string, number>,
    passingStyle: PassingStyle,
    disciplineRisk: DisciplineRisk,
    totalClips: number
  ): PlayerStyleProfile {
    const shortpass = Number(counts['shortpass'] ?? 0);
    const longpass = Number(counts['longpass'] ?? 0);
    const totalPasses = shortpass + longpass;
    const longpassRatio = totalPasses ? longpass / totalPasses : 0;
    const shortpassRatio = totalPasses ? shortpass / totalPasses : 0;
    const attackingRatio = totalClips
      ? (Number(counts['ontarget'] ?? 0) + Number(counts['penalty'] ?? 0) + Number(counts['freekick'] ?? 0) + Number(counts['corner'] ?? 0)) / totalClips
      : 0;
    const setPieceRatio = totalClips
      ? (Number(counts['freekick'] ?? 0) + Number(counts['penalty'] ?? 0) + Number(counts['corner'] ?? 0)) / totalClips
      : 0;
    const foulRatio = totalClips ? Number(counts['foul'] ?? 0) / totalClips : 0;

    const detectedStyles: string[] = [];
    const styleReasons: string[] = [];
    const teamStyles: string[] = [];

    if (shortpassRatio >= 0.7) {
      detectedStyles.push('Possession Player');
      styleReasons.push('The player has a high short pass ratio, showing a tendency to keep possession and connect play.');
      teamStyles.push(...this.teamStylesByProfile['Possession Player']);
    }

    if (longpassRatio >= 0.45) {
      detectedStyles.push('Direct Playmaker');
      styleReasons.push('The player uses long passes frequently, which may help progress the ball quickly or switch play.');
      teamStyles.push(...this.teamStylesByProfile['Direct Playmaker']);
    }

    if (attackingRatio >= 0.25) {
      detectedStyles.push('Attacking Threat Player');
      styleReasons.push('The player appears involved in dangerous attacking situations such as shots on target, penalties, free kicks, or corners.');
      teamStyles.push(...this.teamStylesByProfile['Attacking Threat Player']);
    }

    if (setPieceRatio >= 0.2) {
      detectedStyles.push('Set-Piece Specialist');
      styleReasons.push('The player is frequently involved in set-piece execution such as free kicks, penalties, or corners.');
      teamStyles.push(...this.teamStylesByProfile['Set-Piece Specialist']);
    }

    if (foulRatio >= 0.15) {
      detectedStyles.push('Physical / Aggressive Player');
      styleReasons.push('The player commits fouls frequently, suggesting a more physical or aggressive profile.');
      teamStyles.push(...this.teamStylesByProfile['Physical / Aggressive Player']);
    }

    if (detectedStyles.length === 0) {
      detectedStyles.push('Balanced Player');
      styleReasons.push('No single action type strongly dominates, so the player appears to contribute across different actions.');
      teamStyles.push(...this.teamStylesByProfile['Balanced Player']);
    }

    if (disciplineRisk.risk_level === 'High') {
      styleReasons.push('High foul frequency may increase the risk of conceding dangerous free kicks or receiving cards.');
    }

    return {
      main_style: detectedStyles[0],
      secondary_styles: detectedStyles.slice(1),
      passing_profile: passingStyle.passing_profile,
      discipline_risk: disciplineRisk.risk_level,
      suitable_team_styles: Array.from(new Set(teamStyles)),
      explanation: styleReasons.join(' '),
      limitations_note: 'This is an estimated style profile based only on uploaded single-player clips and model predictions. It does not use full-match tracking, team context, player identity, or timestamps.'
    };
  }

  private buildSuitableTeamStyles(playerProfile: PlayerStyleProfile): SuitableTeamStyles {
    const reasons: Record<string, string> = {
      'Possession Player': 'Primary fit: possession and build-up systems. Secondary traits can add extra role value, but the main match should be a team that wants secure circulation.',
      'Direct Playmaker': 'Primary fit: direct, vertical, and transition-heavy systems. Secondary traits can make the role more attacking or set-piece focused.',
      'Attacking Threat Player': 'Primary fit: teams that need final-third actions and shot involvement. Secondary traits decide whether that threat comes through passing, set pieces, or pressure.',
      'Set-Piece Specialist': 'Primary fit: teams that deliberately create value from corners, free kicks, and penalties. Secondary traits should decide the open-play role.',
      'Physical / Aggressive Player': 'Primary fit: high-pressure or duel-heavy systems. Discipline risk should be managed with clear tactical responsibility.',
      'Balanced Player': 'Primary fit: flexible teams that need adaptable roles rather than one dominant tactical identity.'
    };

    return {
      recommended_team_styles: playerProfile.suitable_team_styles,
      reason: reasons[playerProfile.main_style] ?? reasons['Balanced Player']
    };
  }

  primaryStyleSummary(style: string): string {
    return this.styleSummaries[style] ?? 'The strongest signal in this player profile based on the uploaded clips.';
  }

  secondaryStyleSummary(style: string): string {
    return this.styleSummaries[style] ?? 'A supporting trait that can shape the player role in the right tactical context.';
  }

  teamStyleGroups(fit: SuitableTeamStyles): TeamStyleGroup[] {
    const profile = this.playerProfile;
    if (!profile) {
      return [{
        label: 'Tactical fit',
        title: 'Best tactical environments',
        styles: fit.recommended_team_styles,
        tone: 'main'
      }];
    }

    const groups: TeamStyleGroup[] = [{
      label: 'Best match',
      title: profile.main_style,
      styles: this.stylesForProfile(profile.main_style, fit.recommended_team_styles),
      tone: 'main'
    }];

    for (const style of profile.secondary_styles ?? []) {
      const styles = this.stylesForProfile(style, fit.recommended_team_styles);
      if (styles.length) {
        groups.push({
          label: 'Role support',
          title: style,
          styles,
          tone: style === 'Physical / Aggressive Player' ? 'risk' : 'supporting'
        });
      }
    }

    return groups;
  }

  private stylesForProfile(style: string, fallbackStyles: string[]): string[] {
    const mapped = this.teamStylesByProfile[style] ?? [];
    const fallbackSet = new Set(fallbackStyles);
    const fromSaved = mapped.filter((item) => fallbackSet.has(item));
    return fromSaved.length ? fromSaved : mapped;
  }

  private buildProfileReliability(totalClips: number, averageConfidence: number): ProfileReliability {
    const reliability = totalClips >= 30 && averageConfidence >= 0.85
      ? 'High'
      : totalClips >= 15 && averageConfidence >= 0.75
        ? 'Medium'
        : 'Low';

    return {
      profile_reliability: reliability,
      reason: `The profile is based on ${totalClips} analyzed clips with ${(averageConfidence * 100).toFixed(2)}% average confidence.`
    };
  }

  private computeActionStats(): void {
    const countsByAction = new Map<string, number>();
    for (const action of this.allActions) {
      const key = this.actionKey(action.action);
      countsByAction.set(key, (countsByAction.get(key) ?? 0) + 1);
    }

    const reviewCounts = this.playerReview?.action_counter ?? {};
    const sourceEntries = this.hasReviewCounts(this.playerReview)
      ? this.actionOrder.map((action) => [action, Number(reviewCounts[action] ?? 0)] as [string, number])
      : Array.from(countsByAction.entries());

    this.actionStats = sourceEntries
      .filter(([, count]) => count > 0)
      .map(([action, count]) => ({
        label: action,
        count,
        icon: this.actionIcons[this.actionKey(action)] ?? 'A'
      }))
      .sort((a, b) => b.count - a.count);
  }

  get uniqueActionCount(): number {
    if (this.playerReview?.action_counter) {
      return this.actionOrder.filter((action) => Number(this.playerReview?.action_counter[action] ?? 0) > 0).length;
    }

    return new Set(this.allActions.map((action) => action.action)).size;
  }

  get passingStyle(): PassingStyle | null {
    return this.playerReview?.analysis?.passing_style ?? null;
  }

  get attackingThreat(): AttackingThreat | null {
    return this.playerReview?.analysis?.estimated_attacking_threat ?? null;
  }

  get disciplineRisk(): DisciplineRisk | null {
    return this.playerReview?.analysis?.discipline_risk ?? null;
  }

  get setPieceSummary(): SetPieceSummary | null {
    return this.playerReview?.analysis?.set_piece_summary ?? null;
  }

  get playerProfile(): PlayerStyleProfile | null {
    return this.playerReview?.analysis?.estimated_player_playing_style_profile ?? null;
  }

  get suitableTeamStyles(): SuitableTeamStyles | null {
    return this.playerReview?.analysis?.suitable_team_styles ?? null;
  }

  get profileReliability(): ProfileReliability | null {
    const reliability = this.playerReview?.analysis?.profile_reliability ?? null;
    if (!reliability) return null;

    const avgText = this.averageConfidenceText;
    let reason = reliability.reason;
    
    if (avgText && reason.includes('average confidence')) {
      reason = reason.replace(/with\s+[\d.]+%\s+average confidence/i, `with ${avgText} average confidence`);
    }

    return { ...reliability, reason };
  }

  getActionColor(action: string): string {
    return this.actionColors[this.actionKey(action)] ?? '#6366f1';
  }

  getPercent(count: number): number {
    return this.totalActions === 0 ? 0 : Math.round((count / this.totalActions) * 100);
  }

  percentValue(value: number | undefined | null): number {
    return Math.round(Number(value ?? 0) * 100);
  }

  get averageConfidenceText(): string | null {
    const confidences = this.allActions
      .map((action) => this.normalizeConfidence(action.confidence))
      .filter((confidence) => Number.isFinite(confidence) && confidence > 0);

    if (confidences.length) {
      const average = confidences.reduce((sum, confidence) => sum + confidence, 0) / confidences.length;
      return `${(average * 100).toFixed(1)}%`;
    }

    const reason = this.profileReliability?.reason ?? '';
    const match = reason.match(/with\s+([\d.]+)%\s+average confidence/i);
    if (!match) {
      return null;
    }

    const parsed = Number(match[1]);
    return parsed > 0 ? `${parsed.toFixed(1)}%` : null;
  }

  formatCount(value: number | undefined | null): string {
    return Number(value ?? 0).toLocaleString();
  }

  formatTime(seconds: number): string {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  }

  clearStats(): void {
    this.hasData = false;
    this.allActions = [];
    this.actionStats = [];
    this.videoResults = [];
    this.playerReview = null;
    this.totalActions = 0;
    this.totalDuration = 0;
    this.videosProcessed = 0;
  }

  private normalizeConfidence(value: number | null | undefined): number {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return 0;
    }

    return numeric > 1 ? numeric / 100 : numeric;
  }

  private actionKey(action: string): string {
    return action.toLowerCase().replace(/\s+/g, '-');
  }

  private roundRatio(value: number): number {
    return Math.round(value * 1000) / 1000;
  }
}
