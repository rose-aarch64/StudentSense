import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"
import { AgentApprovalsProvider } from "@/features/agent/agent-approvals"
import { IN_CONTAINER } from "@/app/in-container"
import {
  CircleAlertIcon,
  LayoutGridIcon,
  PlusIcon,
  PlugIcon,
  Task01Icon,
  XIcon,
} from "@/components/ui/icons"

import { FeatureBadge } from "@/components/feature-badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { CitationPanel } from "@/features/chat/citation-panel"
import { consentPlaceholder } from "@/features/chat/model-issue"
import { askEgress } from "@/features/egress/ask-egress"
import { setDestinationsEnabled } from "@/features/egress/api"
import { ExtraUsageNotice } from "@/features/chat/extra-usage/extra-usage-notice"
import { useExtraUsage } from "@/features/chat/extra-usage/extra-usage-store"
import { useSelectedOnClaudePlan } from "@/features/chat/extra-usage/use-selected-on-claude-plan"
import { ModelIssueNotice } from "@/features/chat/model-issue-notice"
import {
  useBlockAgentic,
  useNewChatChoice,
} from "@/features/chat/modes/new-chat-mode"
import { NewChatModeProvider } from "@/features/chat/modes/new-chat-mode-provider"
import { rememberNextNewChatMode } from "@/features/chat/modes/next-new-chat-mode"
import { canSkipThinking } from "@/features/chat/thinking-preference"
import { ThreadPanel } from "@/features/chat/thread-panel"
import { useChatRuntime } from "@/features/chat/use-chat-runtime"
import { useHelpMenuReport } from "@/features/feedback/help-menu-report"
import { JobsDialog } from "@/features/jobs/jobs-dialog"
import type { ImportAccepted } from "@/features/migration/api"
import { ImportBundleButton } from "@/features/migration/import-bundle"
import { modelKey, type ModelSelection } from "@/features/models/selection/api"
import {
  checkAvailability,
  type Availability,
  type ModelIssue,
} from "@/features/models/selection/availability"
import {
  SettingsDialog,
  type SettingsSectionId,
} from "@/features/settings/settings-dialog"
import { SourcesPanel } from "@/features/sources/sources-panel"
import { useSources } from "@/features/sources/use-sources"
import { useWebSources } from "@/features/sources/web/use-web-sources"
import { canPreview } from "@/features/source-preview/can-preview"
import { SourcePreviewPanel } from "@/features/source-preview/source-preview-panel"
import { ArtifactList } from "@/features/studio/artifact-list"
import { ArtifactPanel } from "@/features/studio/artifact-panel"
import { OpenArtifactContext } from "@/features/studio/open-artifact"
import {
  OFFICE_FORMATS,
  OfficeOfferContext,
} from "@/features/office-support/office-offer"
import { StudioPanel } from "@/features/studio/studio-panel"
import { useStudio } from "@/features/studio/use-studio"
import { TitleBarUpdate } from "@/features/updates/title-bar-update"
import type { Workspace, WorkspaceFolder } from "@/features/workspaces/api"
import { useWorkspaces } from "@/features/workspaces/use-workspaces"
import { useStartupReveal } from "@/features/startup/use-startup-reveal"
import { useStableCallback } from "@/hooks/use-stable-callback"
import { onStorageSettingsRequested } from "@/features/storage/open-storage-settings"
import { intl } from "@/i18n/intl"
import { cn } from "@/lib/utils"
import { WorkspaceRail } from "@/features/workspaces/workspace-rail"
import type { PluginsStart } from "@/features/plugins/plugins-settings"
import {
  readRightPanelOpen,
  readSidebarOpen,
  readSourcePreview,
  writeRightPanelOpen,
  writeSidebarOpen,
  writeSourcePreview,
} from "./chrome-prefs"
import {
  ChatColumn,
  ColumnEdge,
  DashboardColumns,
  RightPanelRail,
  SidebarColumn,
} from "./dashboard-columns"
import { LeftSidebar, type SidebarNavAction } from "./left-sidebar"
import { RightPanel } from "./right-panel"
import { CornerToggle, CornerToggleSlot } from "./corner-toggle"
import { RightPanelToggle } from "./right-panel-toggle"
import { CompactColumns } from "./compact-columns"
import { CompactMenuButton, CompactTodoButton } from "./compact-header-buttons"
import { DashboardShell } from "./dashboard-shell"
import { SidebarFooter } from "./sidebar-footer"
import { useAppHeight } from "./use-app-height"
import { useCompactLayout } from "./use-compact-layout"
import { SidebarToggle } from "./sidebar-toggle"
import { useSidebarShortcut } from "./use-sidebar-shortcut"

// Clicking "N sources" in the composer used to switch the right rail to its
// Sources tab. Sources now live in the always-visible left sidebar, so the
// same click just brings that list into view instead.
const LEFT_SOURCES_ID = "workspace-left-sources"
const LEFT_COLUMN_ID = "workspace-left-column"
const RIGHT_PANEL_ID = "workspace-right-panel"

type Inspect =
  | { kind: "citation"; chunkId: number }
  | { kind: "artifact"; artifactId: number }
  | null

function WorkspaceDashboard({
  workspace,
  selection,
  providerAvailable,
  modelIssue,
  needsConsent,
  onModelIssueSettings,
  onAllowModelIssue,
  onModelRequired,
  onModelCheck,
  onModelSelected,
  onOpenLicense,
  onOpenAudioSettings,
  onOpenSpeechSettings,
  onOpenModelSettings,
  onOpenOfficeSupport,
  onOpenPlugins,
  modelsVisited,
  compactRail,
}: {
  workspace: Workspace
  selection: ModelSelection | null
  providerAvailable: boolean
  modelIssue: ModelIssue | null
  onModelCheck: () => void
  needsConsent: boolean
  onModelIssueSettings: () => void
  onAllowModelIssue: () => void
  onModelRequired: () => void
  onModelSelected: (selection: ModelSelection) => void
  onOpenLicense: () => void
  onOpenAudioSettings: () => void
  onOpenSpeechSettings: () => void
  onOpenModelSettings: (section: SettingsSectionId) => void
  onOpenOfficeSupport: () => void
  onOpenPlugins: (start?: PluginsStart) => void
  modelsVisited: number
  // The workspace rail, which a phone shows in the sidebar's sheet.
  compactRail?: ReactNode
}) {
  const reveal = useStartupReveal()
  const compact = useCompactLayout()
  useAppHeight(compact)
  // The phone's drawer, and the to-do list its header button opens. Neither is
  // saved: the drawer starts closed and the desktop's sidebar choice is left be.
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [todosOpen, setTodosOpen] = useState(false)
  const [inspect, setInspect] = useState<Inspect>(null)
  const [rightPanelOpen, setRightPanelOpen] = useState(readRightPanelOpen)
  const [sidebarWanted, setSidebarWanted] = useState(readSidebarOpen)
  const [sourcePreviewId, setSourcePreviewId] = useState<number | null>(() =>
    readSourcePreview(workspace.id)
  )
  const sources = useSources(workspace.id)
  const webSources = useWebSources(workspace.id, sources.addCreated)
  // Which formats Studio offers is the server's answer to what is selected,
  // so it has to be asked again when that changes. The chat model is named
  // here directly; the image model is chosen inside the settings dialog and
  // reported only by `modelsVisited`, which counts closing it.
  const studio = useStudio(
    workspace.id,
    `${selection ? modelKey(selection) : "none"}:${modelsVisited}`
  )
  const selectedSourceTitles = useMemo(() => {
    const titles = new Map(
      sources.documents.map((document) => [document.id, document.title])
    )
    return sources.includedDocumentIds.map((id) => titles.get(id) ?? "")
  }, [sources.documents, sources.includedDocumentIds])
  const mentionables = useMemo(
    () => ({
      documents: sources.documents,
      index: sources.index,
      artifacts: studio.artifacts,
      isLoading: sources.isLoading || studio.isLoading,
    }),
    [
      sources.documents,
      sources.index,
      sources.isLoading,
      studio.artifacts,
      studio.isLoading,
    ]
  )
  const blockAgentic = useBlockAgentic()
  // Bound to the model the chat was asked on: the picker stays open meanwhile.
  const onAgenticGate = useCallback(
    (gate: string) => {
      if (selection) blockAgentic(selection, gate)
    },
    [blockAgentic, selection]
  )
  const chat = useChatRuntime({
    workspaceId: workspace.id,
    canSend: providerAvailable,
    selectedDocumentIds: sources.includedDocumentIds,
    selectedSourceTitles,
    sourceScope: sources.sourceScope,
    readsImages: selection?.reads_images === true,
    canSkipThinking: canSkipThinking(selection),
    newChatMode: useNewChatChoice(selection),
    onAgenticGate,
    onModelRequired,
    onModelCheck,
  })
  const sourcePreview = sources.documents.find(
    (document) => document.id === sourcePreviewId
  )
  const sourcePreviewOpen =
    sourcePreview !== undefined && canPreview(sourcePreview)

  useEffect(() => {
    if (sourcePreviewId === null || sources.isLoading) return
    if (!sourcePreview || !canPreview(sourcePreview)) {
      writeSourcePreview(workspace.id, null)
    }
  }, [sourcePreview, sourcePreviewId, sources.isLoading, workspace.id])

  const composerHold =
    modelIssue && needsConsent ? consentPlaceholder(modelIssue) : undefined
  // A model issue blocks sending, so it takes the composer's one notice first.
  const extraUsage = useExtraUsage()
  const onClaudePlan = useSelectedOnClaudePlan(selection)

  const closeInspect = () => setInspect(null)
  const startNewChat = () => {
    closeInspect()
    chat.startNewChat()
  }
  const closeSourcePreview = () => {
    setSourcePreviewId(null)
    writeSourcePreview(workspace.id, null)
  }
  // Stable, like everything else the memoized sources panel takes: this page
  // re-renders when a run starts, ends or changes state, and for a title, a
  // thread switch, Settings and the other columns.
  const openSpeechSettings = useStableCallback(() => onOpenSpeechSettings())
  const toggleSourcePreview = useStableCallback((documentId: number) => {
    const next = sourcePreviewId === documentId ? null : documentId
    setSourcePreviewId(next)
    writeSourcePreview(workspace.id, next)
  })
  const sourceUploads = useMemo(
    () => ({
      isUploading: sources.isUploading,
      onUpload: sources.upload,
      onUploadFolder: sources.uploadEntries,
    }),
    [sources.isUploading, sources.upload, sources.uploadEntries]
  )
  const sourceNotes = useMemo(
    () => ({
      write: sources.writeNote,
      load: sources.loadNote,
      edit: sources.editNote,
    }),
    [sources.writeNote, sources.loadNote, sources.editNote]
  )
  // Built once per change of what it shows, so the memoized sidebar skips
  // every other render of this page.
  const sourcesList = useMemo(
    () => (
      <aside
        id={LEFT_SOURCES_ID}
        aria-label={intl.formatMessage({
          id: "dashboard_sources_aria",
          defaultMessage: "Workspace sources",
        })}
        className="flex h-full min-h-0 min-w-0 flex-col"
      >
        <SourcesPanel
          workspaceId={workspace.id}
          documents={sources.documents}
          index={sources.index}
          selectedDocumentIds={sources.includedDocumentIds}
          folderTicks={sources.folderTicks}
          highlightedDocumentId={null}
          isLoading={sources.isLoading}
          isDeleting={sources.isDeleting}
          error={sources.error}
          upload={sourceUploads}
          onDropFiles={sources.isUploading ? undefined : sources.uploadEntries}
          onOpen={sources.openOriginal}
          onPreview={toggleSourcePreview}
          onReveal={sources.revealOriginal}
          onRetry={sources.retry}
          onCancel={sources.cancel}
          onDelete={sources.deleteOne}
          onDeleteSelected={sources.deleteSelected}
          onSelectionChange={sources.setDocumentIncluded}
          onFolderSelectionChange={sources.setFolderIncluded}
          onToggleAll={sources.toggleAllIncluded}
          onRename={sources.rename}
          folderActions={sources.folderActions}
          notes={sourceNotes}
          web={webSources}
          transcriptionPaces={sources.transcriptionPaces}
          onOpenSpeechSettings={openSpeechSettings}
        />
      </aside>
    ),
    [
      workspace.id,
      sources.documents,
      sources.index,
      sources.includedDocumentIds,
      sources.folderTicks,
      sources.isLoading,
      sources.isDeleting,
      sources.error,
      sourceUploads,
      sources.isUploading,
      sources.uploadEntries,
      sources.openOriginal,
      toggleSourcePreview,
      sources.revealOriginal,
      sources.retry,
      sources.cancel,
      sources.deleteOne,
      sources.deleteSelected,
      sources.setDocumentIncluded,
      sources.setFolderIncluded,
      sources.toggleAllIncluded,
      sources.rename,
      sources.folderActions,
      sourceNotes,
      webSources,
      sources.transcriptionPaces,
      openSpeechSettings,
    ]
  )
  const sidebarFooter = useMemo(
    () => <SidebarFooter onOpenLicense={onOpenLicense} />,
    [onOpenLicense]
  )
  const [jobsOpen, setJobsOpen] = useState(false)
  const openJobs = useCallback(() => setJobsOpen(true), [])
  // Stable, for the memoized Jobs dialog: the page above makes both anew on
  // each of its renders.
  const openModelSettings = useStableCallback((section: SettingsSectionId) =>
    onOpenModelSettings(section)
  )
  const openLicense = useStableCallback(() => onOpenLicense())
  const sidebarActions = useMemo<SidebarNavAction[]>(
    () => [
      {
        key: "plugins",
        label: intl.formatMessage({
          id: "dashboard_sidebar_plugins_button",
          defaultMessage: "Plugins",
        }),
        icon: PlugIcon,
        onClick: () => onOpenPlugins(),
      },
      {
        key: "jobs",
        label: intl.formatMessage({
          id: "dashboard_sidebar_jobs_button",
          defaultMessage: "Jobs",
        }),
        icon: Task01Icon,
        badge: <FeatureBadge stage="new" />,
        onClick: openJobs,
      },
    ],
    [onOpenPlugins, openJobs]
  )
  // The sidebar's callbacks keep one identity and call the latest chat.
  const sidebarNewChat = useStableCallback(() => startNewChat())
  const sidebarSelectThread = useStableCallback((threadId: number) => {
    if (threadId !== chat.activeThreadId) closeInspect()
    chat.selectThread(threadId)
  })
  const sidebarRenameThread = useStableCallback(
    (threadId: number, title: string) => chat.rename(threadId, title)
  )
  const sidebarDeleteThread = useStableCallback(async (threadId: number) => {
    if (threadId === chat.activeThreadId) closeInspect()
    await chat.removeThread(threadId)
  })
  const sidebarTitleAnimationComplete = useStableCallback(() =>
    chat.finishTitleAnimation()
  )
  // On a phone a choice in the drawer closes it.
  const closeDrawer = useStableCallback(() => setDrawerOpen(false))
  const drawerNewChat = useStableCallback(() => {
    startNewChat()
    setDrawerOpen(false)
  })
  const drawerSelectThread = useStableCallback((threadId: number) => {
    sidebarSelectThread(threadId)
    setDrawerOpen(false)
  })
  // A source preview needs its column, so it shows over a hidden sidebar.
  const sidebarOpen = sidebarWanted || sourcePreviewOpen
  const setSidebar = useStableCallback((open: boolean) => {
    setSidebarWanted(open)
    writeSidebarOpen(open)
  })
  const toggleSidebar = useStableCallback(() => {
    if (sourcePreviewOpen) closeSourcePreview()
    setSidebar(!sidebarOpen)
  })
  useSidebarShortcut(toggleSidebar)
  // Docker's toggle sits in the columns' corner: shown, the logo keeps its
  // room; floated in, the sidebar covers that corner and carries its own.
  const sidebarHeaderStart = useMemo(
    () =>
      !IN_CONTAINER ? null : sidebarOpen ? (
        <CornerToggleSlot className="-ml-1" />
      ) : (
        <SidebarToggle
          open={false}
          controls={LEFT_COLUMN_ID}
          onToggle={toggleSidebar}
          className="-ml-1"
        />
      ),
    [sidebarOpen, toggleSidebar]
  )
  const toggleRightPanel = () => {
    setRightPanelOpen((open) => {
      const next = !open
      writeRightPanelOpen(next)
      return next
    })
  }
  const openRightPanel = useCallback(() => {
    setRightPanelOpen(true)
    writeRightPanelOpen(true)
  }, [])
  // Stable: it is a context value, and a new one would re-render every agent
  // step in the thread.
  const openArtifact = useCallback(
    (artifactId: number) => {
      openRightPanel()
      setInspect({ kind: "artifact", artifactId })
    },
    [openRightPanel]
  )
  // Stable for the same reason.
  const officeOffer = useMemo(() => {
    const office = new Set(
      studio.artifacts
        .filter((made) => OFFICE_FORMATS.has(made.format))
        .map((made) => made.id)
    )
    return {
      isOfficeFile: (artifactId: number) => office.has(artifactId),
      openOfficeSupport: onOpenOfficeSupport,
    }
  }, [studio.artifacts, onOpenOfficeSupport])
  // Stable too: every reply's citations are drawn with it.
  const onCitation = useCallback(
    (chunkId: number) => {
      openRightPanel()
      setInspect({ kind: "citation", chunkId })
    },
    [openRightPanel]
  )
  const rightPanelToggle = (className?: string) => (
    <RightPanelToggle
      open={rightPanelOpen}
      controls={RIGHT_PANEL_ID}
      onToggle={toggleRightPanel}
      className={className}
    />
  )
  // Built once here, so the desktop columns and the phone's sheets place the
  // same content.
  const detailNode =
    inspect?.kind === "citation" ? (
      <CitationPanel
        workspaceId={workspace.id}
        chunkId={inspect.chunkId}
        onClose={closeInspect}
        onOpen={(id) => void sources.openOriginal(id)}
      />
    ) : inspect?.kind === "artifact" ? (
      <ArtifactPanel
        workspaceId={workspace.id}
        artifactId={inspect.artifactId}
        artifacts={studio.artifacts}
        onOpenVersion={openArtifact}
        onRefine={studio.refine}
        onImageEdit={studio.editImage}
        onOpenModelSettings={onOpenModelSettings}
        onDecideAll={studio.decideAll}
        onClose={closeInspect}
      />
    ) : null
  const sidebarNode = (
    <>
      {sourcePreviewOpen && sourcePreview ? (
        <SourcePreviewPanel
          workspaceId={workspace.id}
          document={sourcePreview}
          onOpen={() => void sources.openOriginal(sourcePreview.id)}
          onClose={closeSourcePreview}
        />
      ) : null}
      {/* Hidden, not unmounted, so the sources list keeps its scroll. */}
      <div hidden={sourcePreviewOpen} className="flex h-full min-h-0 flex-col">
        <LeftSidebar
          threads={chat.threads}
          activeThreadId={chat.activeThreadId}
          autoNamingThreadId={chat.autoNamingThreadId}
          animatingTitleThreadId={chat.animatingTitleThreadId}
          isLoadingThreads={chat.isLoadingThreads}
          onNewChat={compact ? drawerNewChat : sidebarNewChat}
          onSelectThread={compact ? drawerSelectThread : sidebarSelectThread}
          onRenameThread={sidebarRenameThread}
          onDeleteThread={sidebarDeleteThread}
          onTitleAnimationComplete={sidebarTitleAnimationComplete}
          runStates={chat.runStates}
          unreadThreadIds={chat.unreadThreadIds}
          actions={sidebarActions}
          headerStart={compact ? null : sidebarHeaderStart}
          sources={sourcesList}
          footer={sidebarFooter}
          todosOpen={compact ? todosOpen : undefined}
          onTodosOpenChange={compact ? setTodosOpen : undefined}
        />
      </div>
    </>
  )
  // A function of the two header slots: the desktop keeps room for its corner
  // toggles there, the phone puts its menu and to-do buttons.
  const renderChat = (headerStart: ReactNode, headerEnd: ReactNode) => (
    <AgentApprovalsProvider
      approvals={chat.approvals}
      answer={chat.answerApproval}
    >
      <ThreadPanel
        headerStart={headerStart}
        headerEnd={headerEnd}
        live={chat.liveThread}
        thread={chat.activeThread}
        view={chat.conversationView}
        model={selection}
        isLoading={chat.isLoadingMessages}
        isRunning={chat.isRunning}
        animateTitle={chat.activeThreadId === chat.animatingTitleThreadId}
        providerAvailable={providerAvailable}
        notice={
          modelIssue ? (
            <ModelIssueNotice
              issue={modelIssue}
              onAllow={needsConsent ? onAllowModelIssue : undefined}
              onOpenSettings={onModelIssueSettings}
            />
          ) : extraUsage && onClaudePlan ? (
            <ExtraUsageNotice usage={extraUsage} />
          ) : null
        }
        blockedPlaceholder={composerHold}
        onCitation={onCitation}
        onModelSetup={onModelRequired}
        onModelSelected={onModelSelected}
        onRetry={chat.retry}
        onNewChat={startNewChat}
        sourceCount={sources.includedDocumentIds.length}
        mentionables={mentionables}
        onUploadSources={(files) => void sources.upload(files)}
        isUploadingSources={sources.isUploading}
        onOpenPlugins={onOpenPlugins}
        dictation={chat.dictation}
        onOpenSpeechSettings={openSpeechSettings}
        onTitleAnimationComplete={chat.finishTitleAnimation}
        autoNamingThreadId={chat.autoNamingThreadId}
        onRename={chat.rename}
        onDelete={async (threadId) => {
          if (threadId === chat.activeThreadId) closeInspect()
          await chat.removeThread(threadId)
        }}
      />
    </AgentApprovalsProvider>
  )
  // Inside the opener, so a run's Open in Studio shows its copy here.
  const jobsDialog = (
    <JobsDialog
      open={jobsOpen}
      onOpenChange={setJobsOpen}
      workspaceId={workspace.id}
      documents={sources.documents}
      includedDocumentIds={sources.includedDocumentIds}
      selection={selection}
      providerAvailable={providerAvailable}
      onUploadSources={sources.upload}
      onOpenModelSettings={openModelSettings}
      onOpenLicense={openLicense}
    />
  )
  // Narrower than the desktop layout fits: one column with the sidebar and the
  // detail as full-screen sheets. The desktop's JSX below is left as it is.
  if (compact) {
    return (
      <OfficeOfferContext.Provider value={officeOffer}>
        <OpenArtifactContext.Provider value={openArtifact}>
          <CompactColumns
            chat={renderChat(
              <CompactMenuButton onClick={() => setDrawerOpen(true)} />,
              <CompactTodoButton onClick={() => setTodosOpen(true)} />
            )}
            rail={compactRail}
            sidebar={sidebarNode}
            drawerOpen={drawerOpen}
            onDrawerClose={closeDrawer}
            detail={detailNode}
            detailOpen={inspect !== null}
            onDetailClose={closeInspect}
          />
          {jobsDialog}
        </OpenArtifactContext.Provider>
      </OfficeOfferContext.Provider>
    )
  }
  return (
    <OfficeOfferContext.Provider value={officeOffer}>
      <OpenArtifactContext.Provider value={openArtifact}>
        <div className="titlebar-controls">
          {/* Docker's browser has no title bar: there it sits beside the logo. */}
          {IN_CONTAINER ? null : (
            <div
              {...reveal}
              className={cn("titlebar-controls-start", reveal.className)}
            >
              <SidebarToggle
                open={sidebarOpen}
                controls={LEFT_COLUMN_ID}
                onToggle={toggleSidebar}
                className="pointer-events-auto size-6"
              />
            </div>
          )}
          <div
            {...reveal}
            className={cn("titlebar-controls-end", reveal.className)}
          >
            <TitleBarUpdate />
            {/* Docker's browser has no title bar: there the toggle sits on a heading's line. */}
            {IN_CONTAINER
              ? null
              : rightPanelToggle("pointer-events-auto size-6")}
          </div>
        </div>
        {/* The widths live in here, so a drag of an edge renders the column
          boxes and edges, not the sidebar, the thread or Studio. */}
        <DashboardColumns
          sidebarOpen={sidebarOpen}
          sidebarWide={sourcePreviewOpen}
          rightPanelOpen={rightPanelOpen}
          rightPanelWide={inspect !== null}
        >
          {/* Docker's browser has no title bar: one toggle pinned to the
            columns' corner, so it never moves as the panel slides. An
            inspected citation or artifact has its own close button there. */}
          {IN_CONTAINER && !(rightPanelOpen && inspect !== null) ? (
            <CornerToggle side="end">{rightPanelToggle()}</CornerToggle>
          ) : null}
          {/* The same on the left; a source preview's header has its own close. */}
          {IN_CONTAINER && !sourcePreviewOpen ? (
            <CornerToggle side="start">
              <SidebarToggle
                open={sidebarOpen}
                controls={LEFT_COLUMN_ID}
                onToggle={toggleSidebar}
              />
            </CornerToggle>
          ) : null}
          {/* A preview takes over the left column and widens it, as an
            inspected artifact does the right one; the right panel stays put.
            On a narrow window it gives way first, down to the sidebar's
            minimum, before the right panel does: the chat keeps its own. */}
          <SidebarColumn id={LEFT_COLUMN_ID} peekable>
            {sidebarNode}
          </SidebarColumn>
          {/* Hidden, the sidebar has no edge to drag. */}
          {sidebarOpen ? (
            <ColumnEdge
              column="sidebar"
              label={intl.formatMessage({
                id: "dashboard_sidebar_resize_aria",
                defaultMessage: "Resize sidebar",
              })}
              controls={LEFT_COLUMN_ID}
            />
          ) : null}
          <ChatColumn>
            {renderChat(
              // Hidden, the chat's header runs under the corner toggle: keep its
              // slot. -ml-3 undoes the 12 px of its px-5 over the corner's 8.
              IN_CONTAINER && !sidebarOpen ? (
                <CornerToggleSlot className="-ml-3" />
              ) : null,
              // Hidden, the chat's header runs under the corner toggle: keep its slot.
              IN_CONTAINER && !rightPanelOpen ? (
                <CornerToggleSlot className="-mr-1" />
              ) : null
            )}
          </ChatColumn>
          {/* Collapsed, the rail has no edge to drag. */}
          {rightPanelOpen ? (
            <ColumnEdge
              column="rightPanel"
              label={intl.formatMessage({
                id: "dashboard_right_panel_resize_aria",
                defaultMessage: "Resize right panel",
              })}
              controls={RIGHT_PANEL_ID}
            />
          ) : null}
          <RightPanelRail open={rightPanelOpen}>
            <div id={RIGHT_PANEL_ID} className="h-full min-h-0">
              <RightPanel
                toggle={
                  IN_CONTAINER ? <CornerToggleSlot className="-mr-1" /> : null
                }
                inspect={detailNode}
                studio={
                  <StudioPanel
                    workspaceId={workspace.id}
                    documents={sources.documents}
                    selectedDocumentIds={sources.includedDocumentIds}
                    sourceScope={sources.sourceScope}
                    onSelectionChange={sources.setDocumentIncluded}
                    onToggleAll={sources.toggleAllIncluded}
                    formats={studio.formats}
                    isCreating={studio.isCreating}
                    error={studio.error}
                    onGenerate={studio.create}
                    onSetUpVoices={onOpenAudioSettings}
                  />
                }
                artifacts={
                  <ArtifactList
                    workspaceId={workspace.id}
                    artifacts={studio.artifacts}
                    formats={studio.formats}
                    isLoading={studio.isLoading}
                    onOpen={openArtifact}
                    onRegenerate={studio.regenerate}
                    onCancel={studio.cancel}
                    onDelete={studio.remove}
                  />
                }
              />
            </div>
          </RightPanelRail>
        </DashboardColumns>
        {jobsDialog}
      </OpenArtifactContext.Provider>
    </OfficeOfferContext.Provider>
  )
}

function WorkspacesEmpty({
  isMutating,
  onCreate,
  onImported,
}: {
  isMutating: boolean
  onCreate: (name: string) => Promise<boolean>
  onImported: (accepted: ImportAccepted) => Promise<void>
}) {
  return (
    <main className="flex h-full items-center justify-center bg-background p-8">
      <div className="flex max-w-sm flex-col items-center text-center">
        <div className="mb-4 flex size-11 items-center justify-center rounded-xl bg-muted">
          <LayoutGridIcon className="size-5" />
        </div>
        <h1 className="font-heading text-xl font-medium">
          {intl.formatMessage({
            id: "dashboard_workspaces_empty",
            defaultMessage: "No workspaces",
          })}
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {intl.formatMessage({
            id: "dashboard_workspaces_empty_body",
            defaultMessage:
              "A workspace keeps a source library and its chats together.",
          })}
        </p>
        <Button
          className="mt-5"
          disabled={isMutating}
          onClick={() =>
            void onCreate(
              intl.formatMessage({
                id: "dashboard_workspaces_default_name_label",
                defaultMessage: "My Workspace",
              })
            )
          }
        >
          <PlusIcon />
          {intl.formatMessage({
            id: "dashboard_workspaces_create_button",
            defaultMessage: "Create workspace",
          })}
        </Button>
        <div className="mt-3">
          <ImportBundleButton onImported={onImported} />
        </div>
      </div>
    </main>
  )
}

const NO_FOLDERS: WorkspaceFolder[] = []

export function DashboardPage({
  selection,
  initialProviderAvailable = false,
  initialAvailability,
  initialWorkspaces,
  initialFolders = NO_FOLDERS,
  onModelUnavailable = () => undefined,
  onModelSelected,
}: {
  selection: ModelSelection | null
  // Shorthand for an `available` or unchecked initial status.
  initialProviderAvailable?: boolean
  // What startup found, so this screen need not check the same model again.
  initialAvailability?: Availability
  initialWorkspaces: Workspace[]
  initialFolders?: WorkspaceFolder[]
  onModelUnavailable?: () => void
  onModelSelected: (selection: ModelSelection) => void
}) {
  const compact = useCompactLayout()
  const workspaces = useWorkspaces(initialWorkspaces, initialFolders)
  const initial: Availability =
    initialAvailability ??
    (initialProviderAvailable
      ? { status: "available" }
      : { status: "checking" })
  // Tagged with the model it describes, so a newly chosen model reads as
  // checking until its own answer arrives, never as the last one's.
  const [checked, setChecked] = useState<{
    key: string | null
    availability: Availability
  }>(() => ({
    key: selection ? modelKey(selection) : null,
    availability: initial,
  }))
  // Startup already checked this model; the first run here would repeat it.
  const skipFirstCheck = useRef(initial.status !== "checking")
  const [settingsOpen, setSettingsOpen] = useState(false)
  // Bumped when the settings dialog closes, because a model can be chosen in
  // there without anything on this screen hearing about it: the image model is
  // selected inside the catalog and never reaches `onModelSelected`.
  const [modelsVisited, setModelsVisited] = useState(0)
  const [settingsSection, setSettingsSection] =
    useState<SettingsSectionId>("general")
  // Bumped after egress is allowed from the notice, to check the model again.
  const [consents, setConsents] = useState(0)
  // Bumped when a send is refused for a reason the check reports, so it says why.
  const [refusedSends, setRefusedSends] = useState(0)

  // Set while Settings opens on Office support's consent, from a thread's offer.
  const [askOfficeConsent, setAskOfficeConsent] = useState(false)

  const openSettings = (section: SettingsSectionId) => {
    setSettingsSection(section)
    setSettingsOpen(true)
  }
  useEffect(
    () =>
      onStorageSettingsRequested(() => {
        setSettingsSection("storage")
        setSettingsOpen(true)
      }),
    []
  )
  const openOfficeSupport = useCallback(() => {
    setAskOfficeConsent(true)
    setSettingsSection("office-support")
    setSettingsOpen(true)
  }, [])
  // Set while Settings opens on Plugins' Browse or Add custom plugin, from the composer.
  const [pluginsStart, setPluginsStart] = useState<PluginsStart>()
  const openPlugins = useCallback((start?: PluginsStart) => {
    setPluginsStart(start)
    setSettingsSection("plugins")
    setSettingsOpen(true)
  }, [])
  // The menu has Settings to go to here, once a workspace renders it;
  // otherwise it opens the dialog.
  useHelpMenuReport(
    () => openSettings("report-issue"),
    Boolean(workspaces.activeWorkspace)
  )

  // For the startup frame, which offers mentions before this loads.
  useEffect(() => rememberNextNewChatMode(selection), [selection])

  // Checked when the model changes, when settings close (a key entered again,
  // egress switched, a connection edited), after egress is allowed, and after a
  // send was refused for Claude Code.
  useEffect(() => {
    if (!selection) return
    if (skipFirstCheck.current) {
      skipFirstCheck.current = false
      return
    }
    const key = modelKey(selection)
    const controller = new AbortController()
    void checkAvailability(selection, controller.signal).then(
      (availability) => {
        if (!controller.signal.aborted) setChecked({ key, availability })
      }
    )
    return () => controller.abort()
  }, [selection, modelsVisited, consents, refusedSends])

  const availability: Availability =
    selection && checked.key === modelKey(selection)
      ? checked.availability
      : { status: "checking" }
  const issue =
    availability.status === "needs-consent" ||
    availability.status === "unusable"
      ? availability.issue
      : null
  // A model gone from its list is set up again from scratch.
  const usableSelection = availability.status === "gone" ? null : selection
  const providerAvailable =
    usableSelection !== null && availability.status !== "unusable"

  const allowModelIssue = () => {
    const destination = issue?.destination
    if (!destination) return
    void askEgress({
      destination,
      host: issue.host ?? "",
      allow: () => setDestinationsEnabled([destination], true),
    }).then((allowed) => {
      if (allowed) setConsents((count) => count + 1)
    })
  }

  const onImported = async (accepted: ImportAccepted) => {
    const first = accepted.workspaces[0]
    await workspaces.reload(first?.id ?? workspaces.activeWorkspace?.id ?? -1)
  }

  if (!workspaces.activeWorkspace) {
    return (
      <WorkspacesEmpty
        isMutating={workspaces.isMutating}
        onCreate={workspaces.create}
        onImported={onImported}
      />
    )
  }

  // Beside the columns on a desktop, in the sidebar's sheet on a phone.
  const rail = (
    <WorkspaceRail
      workspaces={workspaces.workspaces}
      folders={workspaces.folders}
      activeWorkspaceId={workspaces.activeWorkspace.id}
      isMutating={workspaces.isMutating}
      onSelect={workspaces.select}
      onCreate={workspaces.create}
      onRename={workspaces.rename}
      onDelete={workspaces.remove}
      onOpenSettings={() => openSettings("general")}
      onSetIcon={workspaces.setIcon}
      onMoveToFolder={workspaces.moveToFolder}
      onCreateFolder={workspaces.createFolder}
      onRenameFolder={workspaces.renameFolder}
      onDeleteFolder={workspaces.removeFolder}
    />
  )

  return (
    // Above the workspace, so a mode picked for the next chat holds across them.
    <NewChatModeProvider>
      <DashboardShell>
        {compact ? null : rail}
        <WorkspaceDashboard
          key={workspaces.activeWorkspace.id}
          compactRail={compact ? rail : undefined}
          workspace={workspaces.activeWorkspace}
          selection={usableSelection}
          providerAvailable={providerAvailable}
          modelIssue={issue}
          needsConsent={availability.status === "needs-consent"}
          onAllowModelIssue={allowModelIssue}
          onModelIssueSettings={() =>
            openSettings(
              availability.status === "needs-consent"
                ? "network"
                : "chat-models"
            )
          }
          onModelRequired={() => openSettings("chat-models")}
          onModelCheck={() => setRefusedSends((count) => count + 1)}
          onModelSelected={onModelSelected}
          onOpenLicense={() => openSettings("license")}
          onOpenAudioSettings={() => openSettings("audio-models")}
          onOpenSpeechSettings={() => openSettings("speech-models")}
          onOpenModelSettings={openSettings}
          onOpenOfficeSupport={openOfficeSupport}
          onOpenPlugins={openPlugins}
          modelsVisited={modelsVisited}
        />
        <SettingsDialog
          open={settingsOpen}
          section={settingsSection}
          askOfficeConsent={askOfficeConsent}
          pluginsStart={pluginsStart}
          onOpenChange={(open) => {
            setSettingsOpen(open)
            if (!open) {
              setModelsVisited((seen) => seen + 1)
              setAskOfficeConsent(false)
              setPluginsStart(undefined)
            }
          }}
          onSectionChange={(next) => {
            setSettingsSection(next)
            setAskOfficeConsent(false)
            setPluginsStart(undefined)
          }}
          onModelUnavailable={onModelUnavailable}
          onModelSelected={onModelSelected}
          onImported={onImported}
        />
        {workspaces.error ? (
          <Alert
            variant="destructive"
            className="absolute top-4 left-1/2 z-40 w-auto max-w-lg -translate-x-1/2 shadow-lg"
          >
            <CircleAlertIcon />
            <AlertTitle>
              {intl.formatMessage({
                id: "dashboard_workspace_error_title",
                defaultMessage: "Workspace action failed",
              })}
            </AlertTitle>
            <AlertDescription>{workspaces.error}</AlertDescription>
            <Button
              variant="ghost"
              size="icon-sm"
              className="absolute top-1 right-1"
              aria-label={intl.formatMessage({
                id: "dashboard_workspace_error_dismiss_aria",
                defaultMessage: "Dismiss workspace error",
              })}
              onClick={workspaces.clearError}
            >
              <XIcon />
            </Button>
          </Alert>
        ) : null}
      </DashboardShell>
    </NewChatModeProvider>
  )
}
