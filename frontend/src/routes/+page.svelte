<script lang="ts">
	import { currentUser } from '$lib/stores';
	import { listEdits, presignDownload } from '$lib/api';

	type Status =
		| 'COMPLETED'
		| 'PROCESSING'
		| 'QUEUED'
		| 'FAILED';

	interface Edit {
		jobId: string;
		filename: string;
		status: Status;
		createdAt: string;
	}

	let edits = $state<Edit[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	let userId = $derived($currentUser);

	let search = $state('');

	const filteredEdits = $derived.by<Edit[]>(() => {
		if (!search.trim()) return edits;

		const q = search.toLowerCase();

		return edits.filter((e) =>
			e.filename?.toLowerCase().includes(q)
		);
	});

	async function load(user: string) {
		loading = true;
		error = null;

		try {
			const data: { edits: Edit[] } =
				await listEdits(user);

			edits = data.edits ?? [];
		} catch {
			edits = [];
			error = 'Failed to load edits';
		} finally {
			loading = false;
		}
	}

	async function download(jobId: string) {
		if (!userId) return;

		try {
			const { downloadUrl } =
				await presignDownload(userId, jobId);

			window.open(downloadUrl, '_blank');
		} catch {
			alert('Download failed');
		}
	}

	$effect(() => {
		if (!userId) return;
		void load(userId);
	});
</script>

<svelte:head>
	<title>MiniVide</title>
</svelte:head>
{#if loading}
	<p class="muted">Loading…</p>

{:else}
	<h1>
		Your Edits <span class="dim">({userId})</span>
	</h1>

	<!-- Search always visible once loaded -->
	<div class="search">
		<input
			type="text"
			placeholder="Search by filename..."
			bind:value={search}
		/>
	</div>

	{#if edits.length === 0}
		<div class="empty">
			<h2>Nothing here yet</h2>
			<p>Pick a video and start your first edit.</p>
			<a href="/editor" class="cta">Start Editing</a>
		</div>

	{:else if filteredEdits.length === 0}
		<div class="empty">
			<h2>No matches found</h2>
			<p>Try a different filename.</p>
		</div>

	{:else}
		<div class="grid">
			{#each filteredEdits as edit (edit.jobId)}
				<div class="card">
					<div class="card-top">
						<span class="filename" title={edit.filename}>
							{edit.filename}
						</span>

						<span class="badge">
							{edit.status}
						</span>
					</div>

					<div class="card-meta">
						<span>
							{new Date(edit.createdAt).toLocaleString()}
						</span>
					</div>

					<div class="card-actions">
						{#if edit.status === 'COMPLETED'}
							<button
								class="btn-primary"
								onclick={() => download(edit.jobId)}
							>
								Download
							</button>
						{:else}
							<span class="muted small">
								{edit.status}
							</span>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
{/if}