<script>
    import { page } from '$app/state';
    import Editor from '$lib/Editor.svelte';
</script>

<Editor jobId={page.params.jobId || null} />