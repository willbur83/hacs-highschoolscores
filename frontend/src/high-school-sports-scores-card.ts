import { css, html, LitElement, nothing, type PropertyValues } from "lit";

import {
  buildCollapsedHeaderTitle,
  buildHeaderTitle,
  buildMatchupLayout,
  DEFAULT_CARD_GRID_OPTIONS,
  formatFinalStatusLine,
  formatHeroScoreCells,
  formatMatchupVenueLabel,
  formatNextGameStrip,
  formatUpcomingStatusLine,
  resolveCardMode,
  scoreOutcomes,
  teamMonogram,
  type MatchupTeam,
} from "./card-helpers";
import { isProgramEntity } from "./entity-suggestion";
import { selectHeroGame } from "./hero-selection";
import {
  extractScheduleWsError,
  fetchProgramSchedule,
  subscribeProgramScheduleUpdates,
} from "./schedule-client";
import {
  classifySchedulePayload,
  deriveVenueRecordBreakdown,
  formatScheduleMonthDay,
  formatScheduleOpponent,
  formatScheduleResultColumn,
  formatTermEmptyMessage,
  formatTermSectionLabel,
  resolveScheduleNotice,
  shouldShowTermSectionLabel,
  type ScheduleBodyState,
} from "./schedule-helpers";
import type {
  GameAttribute,
  HassEntityState,
  HomeAssistantLike,
  HighSchoolSportsScoresCardConfig,
  ProgramSchedulePayload,
  ScheduleTerm,
} from "./types";
import type { HeroRole } from "./hero-selection";

const CARD_TAG = "high-school-sports-scores-card";
const CARD_TYPE = "custom:high-school-sports-scores-card";

export class HighSchoolSportsScoresCard extends LitElement {
  static properties = {
    hass: { type: Object, attribute: false },
    config: { type: Object, attribute: false },
  };

  declare hass?: HomeAssistantLike;

  declare config?: HighSchoolSportsScoresCardConfig;

  private _expanded = false;

  private _schedulePayload: ProgramSchedulePayload | null = null;

  private _scheduleLoading = false;

  private _scheduleError: string | null = null;

  private _scheduleFetchGeneration = 0;

  private _scheduleUnsubscribe: (() => void) | null = null;

  private _scheduleSubscribedEntity: string | null = null;

  private _scheduleSubscribeGeneration = 0;

  private _scheduleActive = false;

  private _resizeObserver: ResizeObserver | undefined;

  private _resizeObservedElement: Element | null = null;

  private _layoutNotifyFrame: number | null = null;

  private _brokenLogoUrls = new Set<string>();

  public setConfig(config: HighSchoolSportsScoresCardConfig): void {
    if (!config.entity) {
      throw new Error("entity is required");
    }
    const previousEntity = this.config?.entity;
    this.config = config;
    if (previousEntity && previousEntity !== config.entity) {
      this._expanded = false;
      this._brokenLogoUrls.clear();
      this._resetScheduleState();
    }
  }

  public static getStubConfig(): HighSchoolSportsScoresCardConfig {
    return {
      entity: "",
      mode: "both",
      grid_options: { ...DEFAULT_CARD_GRID_OPTIONS },
    };
  }

  public static getConfigForm() {
    return {
      schema: [
        {
          name: "entity",
          required: true,
          selector: { entity: { domain: "sensor" } },
        },
        {
          name: "mode",
          selector: {
            select: {
              options: [
                { value: "both", label: "Last/Next + Schedule" },
                { value: "last_next", label: "Last/Next only" },
                { value: "schedule", label: "Schedule only" },
              ],
            },
          },
        },
      ],
      computeHelper: (schema: { name?: string }, data: HighSchoolSportsScoresCardConfig) => {
        if (schema.name === "entity") {
          return "High School Sports Scores program sensor for last/next games and full schedule.";
        }
        if (schema.name === "mode") {
          if (data.mode === "last_next") {
            return "Game card without the expandable schedule.";
          }
          if (data.mode === "schedule") {
            return "Full schedule and results.";
          }
          return "Game card; click to view the full schedule.";
        }
        return undefined;
      },
      assertConfig: (config: HighSchoolSportsScoresCardConfig) => {
        const mode = config.mode;
        if (mode != null && mode !== "both" && mode !== "last_next" && mode !== "schedule") {
          throw new Error(`Invalid mode: ${String(mode)}`);
        }
      },
    };
  }

  public getCardSize(): number {
    return this._computeCardSizeUnits();
  }

  public getGridOptions() {
    return { ...DEFAULT_CARD_GRID_OPTIONS };
  }

  disconnectedCallback(): void {
    this._resizeObserver?.disconnect();
    this._resizeObservedElement = null;
    if (this._layoutNotifyFrame !== null) {
      cancelAnimationFrame(this._layoutNotifyFrame);
      this._layoutNotifyFrame = null;
    }
    this._teardownSchedule();
    super.disconnectedCallback();
  }

  protected firstUpdated(): void {
    queueMicrotask(() => this._observeCardRoot());
  }

  protected updated(changed: PropertyValues<this>): void {
    if (changed.has("config") || changed.has("hass")) {
      queueMicrotask(() => {
        if (this.isConnected) {
          this._syncScheduleLifecycle();
        }
      });
    }
    queueMicrotask(() => {
      if (this.isConnected) {
        this._observeCardRoot();
      }
    });
  }

  private _computeCardSizeUnits(): number {
    const mode = resolveCardMode(this.config?.mode);
    if (mode === "last_next") {
      return 3;
    }
    if (mode === "both" && !this._expanded) {
      return 3;
    }
    const gameCount = this._countScheduleGames();
    return Math.min(18, Math.max(5, 4 + Math.ceil(gameCount / 2)));
  }

  private _countScheduleGames(): number {
    const payload = this._schedulePayload;
    if (!payload?.terms?.length) {
      return 8;
    }
    let count = 0;
    for (const term of payload.terms) {
      count += term.games?.length ?? 0;
    }
    return count > 0 ? count : 8;
  }

  private _notifyLayoutSizeChange(): void {
    if (this._layoutNotifyFrame !== null) {
      cancelAnimationFrame(this._layoutNotifyFrame);
    }
    this._layoutNotifyFrame = requestAnimationFrame(() => {
      this._layoutNotifyFrame = null;
      this.dispatchEvent(new Event("card-refresh", { bubbles: true, composed: true }));
    });
  }

  private _observeCardRoot(): void {
    const card = this.shadowRoot?.querySelector("ha-card");
    if (!card) {
      return;
    }
    if (!this._resizeObserver) {
      let scheduled = false;
      this._resizeObserver = new ResizeObserver(() => {
        if (scheduled) {
          return;
        }
        scheduled = true;
        requestAnimationFrame(() => {
          scheduled = false;
          this._notifyLayoutSizeChange();
        });
      });
    }
    if (this._resizeObservedElement !== card) {
      this._resizeObserver.disconnect();
      this._resizeObserver.observe(card);
      this._resizeObservedElement = card;
    }
  }

  private _resetScheduleState(): void {
    this._scheduleFetchGeneration += 1;
    this._scheduleSubscribeGeneration += 1;
    this._teardownScheduleSubscription();
    this._schedulePayload = null;
    this._scheduleLoading = false;
    this._scheduleError = null;
    this._scheduleActive = false;
  }

  private _shouldShowSchedule(): boolean {
    const mode = resolveCardMode(this.config?.mode);
    if (mode === "schedule") {
      return true;
    }
    return mode === "both" && this._expanded;
  }

  private _isInteractiveBothMode(): boolean {
    return resolveCardMode(this.config?.mode) === "both";
  }

  private _syncScheduleLifecycle(): void {
    if (!this._shouldShowSchedule()) {
      if (this._scheduleActive) {
        this._teardownSchedule();
        this._scheduleActive = false;
      }
      return;
    }

    const entityId = this.config?.entity;
    if (!entityId || !this.hass) {
      return;
    }

    const state = this.hass.states[entityId];
    if (!state || state.state === "unavailable") {
      if (this._scheduleActive) {
        this._teardownSchedule();
        this._scheduleActive = false;
      }
      return;
    }

    if (this._scheduleSubscribedEntity && this._scheduleSubscribedEntity !== entityId) {
      this._resetScheduleState();
    }

    if (!this._scheduleActive) {
      this._scheduleActive = true;
      void this._fetchSchedule(entityId);
    }

    void this._ensureScheduleSubscribed(entityId);
  }

  private _teardownSchedule(): void {
    this._scheduleFetchGeneration += 1;
    this._scheduleSubscribeGeneration += 1;
    this._teardownScheduleSubscription();
    this._scheduleLoading = false;
  }

  private _teardownScheduleSubscription(): void {
    if (this._scheduleUnsubscribe) {
      this._scheduleUnsubscribe();
      this._scheduleUnsubscribe = null;
    }
    this._scheduleSubscribedEntity = null;
  }

  private async _fetchSchedule(entityId: string): Promise<void> {
    if (!this.hass?.callWS) {
      return;
    }

    const generation = this._scheduleFetchGeneration + 1;
    this._scheduleFetchGeneration = generation;
    this._scheduleLoading = true;
    this._scheduleError = null;
    this.requestUpdate();

    try {
      const payload = await fetchProgramSchedule(this.hass, entityId);
      if (!this._isFetchCurrent(generation, entityId)) {
        return;
      }
      this._schedulePayload = payload;
      this._scheduleError = null;
    } catch (error) {
      if (!this._isFetchCurrent(generation, entityId)) {
        return;
      }
      this._schedulePayload = null;
      this._scheduleError = extractScheduleWsError(error);
    } finally {
      if (this._isFetchCurrent(generation, entityId)) {
        this._scheduleLoading = false;
        this.requestUpdate();
        this._notifyLayoutSizeChange();
      }
    }
  }

  private _isFetchCurrent(generation: number, entityId: string): boolean {
    return (
      generation === this._scheduleFetchGeneration &&
      this._shouldShowSchedule() &&
      this.config?.entity === entityId &&
      this.isConnected
    );
  }

  private _handleScheduleNotify(entityId: string): void {
    if (!this._shouldShowSchedule() || this.config?.entity !== entityId) {
      return;
    }
    void this._fetchSchedule(entityId);
  }

  private async _ensureScheduleSubscribed(entityId: string): Promise<void> {
    if (!this.hass?.connection?.subscribeMessage) {
      return;
    }
    if (this._scheduleSubscribedEntity === entityId && this._scheduleUnsubscribe) {
      return;
    }

    this._teardownScheduleSubscription();
    const generation = this._scheduleSubscribeGeneration + 1;
    this._scheduleSubscribeGeneration = generation;

    try {
      const unsubscribe = await subscribeProgramScheduleUpdates(
        this.hass,
        entityId,
        () => {
          this._handleScheduleNotify(entityId);
        },
      );
      if (
        generation !== this._scheduleSubscribeGeneration ||
        !this._shouldShowSchedule() ||
        this.config?.entity !== entityId ||
        !this.isConnected
      ) {
        unsubscribe();
        return;
      }
      this._scheduleUnsubscribe = unsubscribe;
      this._scheduleSubscribedEntity = entityId;
    } catch {
      // Keep the last successful fetch visible when subscription setup fails.
    }
  }

  private _toggleExpanded(event: Event): void {
    event.stopPropagation();
    if (!this._isInteractiveBothMode()) {
      return;
    }
    this._expanded = !this._expanded;
    this._syncScheduleLifecycle();
    this.requestUpdate();
    this._notifyLayoutSizeChange();
  }

  private _handleExpandKeydown(event: KeyboardEvent): void {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    event.preventDefault();
    this._toggleExpanded(event);
  }

  private _resolveScheduleBody(): ScheduleBodyState {
    if (this._scheduleLoading && !this._schedulePayload && !this._scheduleError) {
      return { kind: "loading" };
    }
    if (this._scheduleError) {
      return {
        kind: "error",
        message: this._scheduleError,
      };
    }
    if (!this._schedulePayload) {
      return { kind: "loading" };
    }
    return classifySchedulePayload(this._schedulePayload);
  }

  protected render() {
    if (!this.config) {
      return nothing;
    }

    const entityId = this.config.entity;
    const mode = resolveCardMode(this.config.mode);
    const state = this.hass?.states[entityId];

    if (!state) {
      return this._renderMessageCard(`Entity not found: ${entityId}`);
    }

    if (state.state === "unavailable") {
      return this._renderMessageCard(`${entityId} is unavailable`);
    }

    if (mode === "schedule") {
      return this._renderScheduleCard(state);
    }

    if (mode === "both" && this._expanded) {
      return this._renderScheduleCard(state, { interactiveBoth: true });
    }

    return this._renderCollapsedCard(state);
  }

  private _renderMessageCard(message: string) {
    return html`
      <ha-card>
        <div class="card-content message">${message}</div>
      </ha-card>
    `;
  }

  private _renderScheduleCard(
    state: HassEntityState,
    options: { interactiveBoth?: boolean } = {},
  ) {
    const attributes = state.attributes;
    const header = buildHeaderTitle(attributes);
    const teamRecord = attributes.team_record;
    const scheduleBody = this._resolveScheduleBody();
    const interactiveBoth = options.interactiveBoth === true;

    return html`
      <ha-card>
        <div
          class="card-content program-card ${interactiveBoth ? "program-card--interactive" : ""}"
          role=${interactiveBoth ? "button" : nothing}
          tabindex=${interactiveBoth ? "0" : nothing}
          aria-expanded=${interactiveBoth ? "true" : nothing}
          @click=${interactiveBoth ? this._toggleExpanded : nothing}
          @keydown=${interactiveBoth ? this._handleExpandKeydown : nothing}
        >
          <header class="chrome chrome--schedule">
            <div class="chrome-title">${header}</div>
          </header>

          ${teamRecord
            ? html`<div class="record-summary">${teamRecord}</div>`
            : nothing}
          ${this._renderRecordBreakdown(scheduleBody)}

          ${this._renderScheduleBody(scheduleBody, attributes.next_game?.id)}
        </div>
      </ha-card>
    `;
  }

  private _renderRecordBreakdown(body: ScheduleBodyState) {
    if (body.kind !== "ready" || !body.payload) {
      return nothing;
    }
    const breakdown = deriveVenueRecordBreakdown(body.payload);
    if (!breakdown) {
      return nothing;
    }
    return html`<div class="record-breakdown">${breakdown}</div>`;
  }

  private _renderScheduleBody(
    body: ScheduleBodyState,
    nextGameId?: string,
  ) {
    if (body.kind === "loading") {
      return html`<div class="schedule-state">Loading schedule…</div>`;
    }
    if (body.kind === "error") {
      return html`<div class="schedule-state schedule-state--error">${body.message}</div>`;
    }
    if (body.kind === "empty-resolved") {
      return html`<div class="schedule-state">${body.message}</div>`;
    }
    if (body.kind === "unresolved" || body.kind === "waiting") {
      return html`<div class="schedule-state schedule-state--unavailable">${body.message}</div>`;
    }

    const payload = body.payload;
    if (!payload) {
      return nothing;
    }

    const notice = resolveScheduleNotice(payload);

    return html`
      <div class="schedule-section" aria-label="Schedule and results">
        ${notice ? this._renderScheduleNotice(notice) : nothing}
        <h3 class="schedule-section-title">Schedule & Results</h3>
        ${payload.terms.map((term) =>
          this._renderScheduleTerm(term, payload.terms, nextGameId),
        )}
      </div>
    `;
  }

  private _renderScheduleNotice(notice: ReturnType<typeof resolveScheduleNotice>) {
    if (!notice) {
      return nothing;
    }
    const modifier =
      notice.kind === "rollover" ? "schedule-notice--rollover" : "schedule-notice--stale";
    return html`
      <p class="schedule-notice ${modifier}" role="note">${notice.message}</p>
    `;
  }

  private _renderScheduleTerm(
    term: ScheduleTerm,
    allTerms: ScheduleTerm[],
    nextGameId?: string,
  ) {
    const showSectionLabel = shouldShowTermSectionLabel(allTerms);
    const games = term.games;

    return html`
      <section class="schedule-term">
        ${showSectionLabel
          ? html`<h3 class="schedule-term-label">${formatTermSectionLabel(term)}</h3>`
          : nothing}
        ${games.length === 0
          ? html`<div class="schedule-term-empty">${formatTermEmptyMessage(term)}</div>`
          : html`
              <div class="schedule-table">
                <div class="schedule-table-head" aria-hidden="true">
                  <span>Date</span>
                  <span>Opponent</span>
                  <span>Result</span>
                </div>
                <ul class="schedule-rows">
                  ${games.map((game) => this._renderScheduleRow(game, nextGameId))}
                </ul>
              </div>
            `}
      </section>
    `;
  }

  private _renderScheduleRow(game: GameAttribute, nextGameId?: string) {
    const dateCell = formatScheduleMonthDay(game.date);
    const opponent = formatScheduleOpponent(game);
    const result = formatScheduleResultColumn(game);
    const highlighted = nextGameId != null && game.id === nextGameId;

    return html`
      <li class="schedule-row ${highlighted ? "schedule-row--next" : ""}">
        <span class="schedule-row-date">${dateCell}</span>
        <span class="schedule-row-opponent">${opponent}</span>
        <span class="schedule-row-result">${result}</span>
      </li>
    `;
  }

  private _renderCollapsedCard(state: HassEntityState) {
    const attributes = state.attributes;
    const title = buildCollapsedHeaderTitle(attributes);
    const teamRecord = attributes.team_record?.trim();
    const year = attributes.year?.trim();
    const selection = selectHeroGame(
      attributes.last_game,
      attributes.next_game,
      new Date(),
    );
    const interactive = this._isInteractiveBothMode();
    const showNextStrip =
      selection?.heroRole === "last" &&
      selection.secondary != null &&
      selection.secondaryRole === "next";

    return html`
      <ha-card>
        <div
          class="card-content program-card hsss-card ${interactive ? "program-card--interactive" : ""}"
          role=${interactive ? "button" : nothing}
          tabindex=${interactive ? "0" : nothing}
          aria-expanded=${interactive ? String(this._expanded) : nothing}
          @click=${interactive ? this._toggleExpanded : nothing}
          @keydown=${interactive ? this._handleExpandKeydown : nothing}
        >
          <header class="hsss-header">
            <div class="hsss-title">${title}</div>
            ${year || teamRecord
              ? html`
                  <div class="hsss-header-meta">
                    ${year ? html`<span class="hsss-year">${year}</span>` : nothing}
                    ${teamRecord
                      ? html`<span class="hsss-record">${teamRecord}</span>`
                      : nothing}
                  </div>
                `
              : nothing}
          </header>
          <hr class="hsss-divider" />

          ${selection
            ? this._renderHero(attributes, selection.hero, selection.heroRole)
            : html`<div class="empty">No last or next game is available.</div>`}

          ${showNextStrip
            ? this._renderNextStrip(selection!.secondary!)
            : nothing}
        </div>
      </ha-card>
    `;
  }

  private _renderHero(
    attributes: HassEntityState["attributes"],
    game: GameAttribute,
    heroRole: HeroRole,
  ) {
    const layout = buildMatchupLayout(attributes, game);
    const isFinal = game.status === "final";
    const ariaLabel = heroRole === "last" ? "Last game" : "Next game";

    if (isFinal) {
      return this._renderFinalHero(layout, game, ariaLabel);
    }
    return this._renderUpcomingHero(layout, game, ariaLabel);
  }

  private _renderFinalHero(
    layout: ReturnType<typeof buildMatchupLayout>,
    game: GameAttribute,
    ariaLabel: string,
  ) {
    const scores = formatHeroScoreCells(layout);
    const outcomes = scoreOutcomes(layout);
    const statusLine = formatFinalStatusLine(game.date);

    return html`
      <section class="hsss-hero hero" aria-label="${ariaLabel}">
        <div class="hsss-body">
          ${this._renderTeamChip(layout.away, "left")}
          <div class="hsss-center hsss-center--scores">
            <span
              class="hsss-score ${outcomes.away === "lose" ? "hsss-score--lose" : ""}"
            >${scores?.away ?? "—"}</span>
            <span
              class="hsss-score ${outcomes.home === "lose" ? "hsss-score--lose" : ""}"
            >${scores?.home ?? "—"}</span>
          </div>
          ${this._renderTeamChip(layout.home, "right")}
        </div>
        <div class="hsss-status hsss-status--final">${statusLine}</div>
      </section>
    `;
  }

  private _renderUpcomingHero(
    layout: ReturnType<typeof buildMatchupLayout>,
    game: GameAttribute,
    ariaLabel: string,
  ) {
    const venueLabel = formatMatchupVenueLabel(game);
    const statusLine = formatUpcomingStatusLine(game.date);

    return html`
      <section class="hsss-hero hero" aria-label="${ariaLabel}">
        <div class="hsss-body">
          ${this._renderTeamChip(layout.away, "left")}
          <div class="hsss-center hsss-center--matchup">${venueLabel}</div>
          ${this._renderTeamChip(layout.home, "right")}
        </div>
        ${statusLine
          ? html`<div class="hsss-status hsss-status--upcoming">${statusLine}</div>`
          : nothing}
      </section>
    `;
  }

  private _renderNextStrip(game: GameAttribute) {
    return html`
      <div class="hsss-next" aria-label="Next game">${formatNextGameStrip(game)}</div>
    `;
  }

  private _renderTeamChip(team: MatchupTeam, side: "left" | "right") {
    return html`
      <div class="hsss-team ${side}">
        ${this._renderLogoTile(team)}
        <span class="hsss-team-name">${team.displayName}</span>
      </div>
    `;
  }

  private _renderLogoTile(team: MatchupTeam) {
    const logoUrl = team.logoUrl;
    const showLogo = Boolean(logoUrl) && !this._brokenLogoUrls.has(logoUrl!);
    if (showLogo && logoUrl) {
      return html`
        <span class="hsss-logo-tile hsss-logo-tile--image">
          <img
            class="hsss-logo"
            src=${logoUrl}
            alt=""
            @error=${() => this._markLogoBroken(logoUrl)}
          />
        </span>
      `;
    }
    const monogram = teamMonogram(team.displayName);
    return html`
      <span
        class="hsss-logo-tile hsss-logo-tile--monogram"
        style="--hsss-mono-hue: ${monogram.hue}"
      >${monogram.initial}</span>
    `;
  }

  private _markLogoBroken(logoUrl: string): void {
    this._brokenLogoUrls.add(logoUrl);
    this.requestUpdate();
  }

  static styles = css`
    :host {
      display: block;
    }

    ha-card {
      display: block;
      background: var(--ha-card-background, var(--card-background-color));
      overflow: hidden;
      container-type: inline-size;
      container-name: hsss-card;
    }

    .card-content {
      padding: 12px 14px;
      color: var(--primary-text-color, #212121);
    }

    .message {
      color: var(--secondary-text-color, #757575);
    }

    .program-card--interactive {
      cursor: pointer;
    }

    .program-card--interactive:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }

    .chrome {
      text-align: left;
      margin-bottom: 10px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
    }

    .chrome--schedule {
      margin-bottom: 12px;
      padding-bottom: 10px;
    }

    .chrome-title {
      font-size: 0.95em;
      font-weight: 500;
      line-height: 1.35;
    }

    .chrome-record {
      margin-top: 4px;
      color: var(--secondary-text-color, #757575);
      font-size: 0.85em;
    }

    .record-summary {
      font-size: 1.35em;
      font-weight: 600;
      line-height: 1.2;
      color: var(--primary-text-color, #212121);
      margin-bottom: 6px;
    }

    .record-breakdown {
      color: var(--secondary-text-color, #757575);
      font-size: 0.82em;
      line-height: 1.4;
      margin-bottom: 14px;
    }

    .schedule-notice {
      margin: 0 0 10px;
      font-size: 0.78em;
      line-height: 1.4;
      color: var(--secondary-text-color, #757575);
    }

    .schedule-notice--rollover {
      font-size: 0.8em;
    }

    .schedule-notice--stale {
      font-size: 0.74em;
      opacity: 0.88;
    }

    .schedule-section-title {
      margin: 0 0 10px;
      font-size: 0.82em;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--secondary-text-color, #757575);
    }

    .schedule-section {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .schedule-state {
      color: var(--secondary-text-color, #757575);
      text-align: center;
      padding: 12px 0 4px;
      line-height: 1.4;
    }

    .schedule-state--error,
    .schedule-state--unavailable {
      color: var(--error-color, #db4437);
    }

    .schedule-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .schedule-table {
      display: flex;
      flex-direction: column;
      gap: 0;
    }

    .schedule-table-head,
    .schedule-row {
      display: grid;
      grid-template-columns: 4.75rem minmax(0, 1fr) max-content;
      column-gap: 12px;
      align-items: start;
    }

    .schedule-table-head {
      padding: 0 0 6px;
      border-bottom: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
      font-size: 0.68em;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--secondary-text-color, #757575);
    }

    .schedule-table-head span:last-child,
    .schedule-row-result {
      text-align: right;
      justify-self: end;
    }

    .schedule-term-label {
      margin: 0 0 8px;
      font-size: 0.82em;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--secondary-text-color, #757575);
    }

    .schedule-term-empty {
      color: var(--secondary-text-color, #757575);
      font-size: 0.85em;
      padding: 4px 0;
    }

    .schedule-rows {
      list-style: none;
      margin: 0;
      padding: 0;
    }

    .schedule-row {
      padding: 7px 0;
      border-top: 1px solid var(--divider-color, rgba(0, 0, 0, 0.08));
      font-size: 0.82em;
      line-height: 1.35;
    }

    .schedule-row:first-child {
      border-top: none;
    }

    .schedule-row--next {
      background: color-mix(
        in srgb,
        var(--primary-color, #03a9f4) 10%,
        transparent
      );
      border-radius: calc(var(--ha-card-border-radius, 12px) * 0.5);
      margin: 0 -4px;
      padding-left: 4px;
      padding-right: 4px;
    }

    .schedule-row-date {
      color: var(--primary-text-color, #212121);
      white-space: nowrap;
    }

    .schedule-row-opponent {
      color: var(--primary-text-color, #212121);
      word-break: break-word;
      min-width: 0;
    }

    .schedule-row-result {
      color: var(--secondary-text-color, #757575);
      white-space: nowrap;
    }

    .hsss-card {
      --hsss-logo-size: 28px;
      --hsss-name-size: 0.9375rem;
      --hsss-score-size: 2rem;
      --hsss-grid-gap: 12px;
      --hsss-chip-pad: 5px 10px;
      --hsss-center-min: 108px;
    }

    .hsss-header {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
      margin-bottom: 8px;
    }

    .hsss-title {
      min-width: 0;
      font-size: 0.9375rem;
      font-weight: 600;
      line-height: 1.3;
      color: var(--primary-text-color);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .hsss-header-meta {
      display: flex;
      align-items: baseline;
      gap: 8px;
      flex-shrink: 0;
    }

    .hsss-year {
      font-size: 0.75rem;
      color: var(--secondary-text-color);
    }

    .hsss-record {
      flex-shrink: 0;
      font-size: 0.8125rem;
      font-weight: 600;
      color: var(--secondary-text-color);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }

    .hsss-divider {
      display: block;
      height: 0;
      margin: 0 0 10px;
      border: 0;
      border-top: 1px solid var(--divider-color);
    }

    .hsss-body {
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      gap: var(--hsss-grid-gap);
    }

    .hsss-team {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      box-sizing: border-box;
      max-width: 100%;
      min-width: 0;
      padding: var(--hsss-chip-pad);
      border-radius: 999px;
      background: color-mix(in srgb, var(--primary-text-color) 4.5%, transparent);
      border: 1px solid color-mix(in srgb, var(--primary-text-color) 8%, transparent);
    }

    .hsss-team.left {
      justify-self: start;
    }

    .hsss-team.right {
      justify-self: end;
      flex-direction: row-reverse;
    }

    @supports (background: light-dark(white, black)) {
      .hsss-team {
        background: light-dark(rgba(0, 0, 0, 0.035), rgba(255, 255, 255, 0.045));
        border: 1px solid light-dark(rgba(0, 0, 0, 0.07), rgba(255, 255, 255, 0.08));
      }
    }

    .hsss-logo-tile {
      box-sizing: border-box;
      flex-shrink: 0;
      width: var(--hsss-logo-size);
      height: var(--hsss-logo-size);
      border-radius: 50%;
    }

    .hsss-logo-tile--image {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2px;
      background: #fff;
      border: 1px solid rgba(0, 0, 0, 0.18);
    }

    .hsss-logo {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }

    @media (prefers-color-scheme: dark) {
      .hsss-logo {
        filter: brightness(0.94);
      }
    }

    .hsss-logo-tile--monogram {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 0.8125rem;
      font-weight: 600;
      line-height: 1;
      color: #fff;
      background: hsl(var(--hsss-mono-hue, 220) 45% 35%);
    }

    .hsss-team-name {
      min-width: 0;
      font-size: var(--hsss-name-size);
      font-weight: 600;
      line-height: 1.2;
      color: var(--primary-text-color);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .hsss-center--scores {
      display: flex;
      gap: 14px;
      justify-content: center;
      min-width: var(--hsss-center-min);
      flex-shrink: 0;
    }

    .hsss-score {
      font-size: var(--hsss-score-size);
      font-weight: 700;
      line-height: 1;
      color: var(--primary-text-color);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }

    .hsss-score--lose {
      opacity: 0.42;
    }

    @media (prefers-color-scheme: dark) {
      .hsss-score--lose {
        opacity: 0.5;
      }
    }

    .hsss-center--matchup {
      min-width: 52px;
      text-align: center;
      font-size: 0.8125rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--secondary-text-color);
      white-space: nowrap;
    }

    .hsss-status {
      margin-top: 8px;
      text-align: center;
      letter-spacing: 0.02em;
      white-space: nowrap;
      line-height: 1.3;
    }

    .hsss-status--final {
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--secondary-text-color);
    }

    .hsss-status--upcoming {
      font-size: 0.8125rem;
      font-weight: 500;
      color: color-mix(in srgb, var(--primary-text-color) 80%, transparent);
    }

    .hsss-next {
      margin-top: 8px;
      padding-top: 6px;
      border-top: 1px solid var(--divider-color);
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--secondary-text-color);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    @container hsss-card (max-width: 379px) {
      .hsss-card {
        --hsss-logo-size: 24px;
        --hsss-name-size: 0.875rem;
        --hsss-score-size: 1.75rem;
        --hsss-grid-gap: 8px;
        --hsss-chip-pad: 4px 8px;
        --hsss-center-min: 88px;
      }
    }

    .empty {
      color: var(--secondary-text-color, #757575);
      text-align: center;
      padding: 12px 0 4px;
    }
  `;
}

declare global {
  interface Window {
    __hsssCardBootstrapped?: boolean;
    customCards?: Array<{
      type: string;
      name: string;
      description?: string;
      preview?: boolean;
      getEntitySuggestion?: (
        hass: HomeAssistantLike,
        entityId: string,
      ) => { config: HighSchoolSportsScoresCardConfig; label?: string } | null;
    }>;
  }
}

function bootstrapHighSchoolSportsScoresCard(): void {
  if (window.__hsssCardBootstrapped) {
    return;
  }
  window.__hsssCardBootstrapped = true;

  if (!customElements.get(CARD_TAG)) {
    customElements.define(CARD_TAG, HighSchoolSportsScoresCard);
  }

  window.customCards = window.customCards ?? [];
  if (!window.customCards.some((entry) => entry.type === CARD_TAG)) {
    window.customCards.push({
      // Picker registry type omits the Lovelace custom: prefix; card configs keep it.
      type: CARD_TAG,
      name: "High School Sports Scores",
      description: "High school sports program card",
      preview: true,
      getEntitySuggestion: (hass, entityId) => {
        if (!isProgramEntity(hass, entityId)) {
          return null;
        }
        return {
          config: {
            type: CARD_TYPE,
            entity: entityId,
            mode: "both",
            grid_options: { ...DEFAULT_CARD_GRID_OPTIONS },
          },
        };
      },
    });
  }
}

bootstrapHighSchoolSportsScoresCard();
