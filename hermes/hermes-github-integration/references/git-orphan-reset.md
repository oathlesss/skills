# Repo Reset via Orphan Branch

Use this when you need to wipe a repo's history on main while archiving the old state to a branch.

## Steps

```bash
# 1. Archive current state
git branch archive/v1
git push -u origin archive/v1

# 2. Create orphan from main
git checkout --orphan tmp-empty
git rm -rf --cached .

# 3. Add only the files you want to keep
git add KEEP_THIS.md
git commit -m "Fresh start"

# 4. ⚠️ CRITICAL: Clean the working tree BEFORE switching back
# The orphan branch has no tracked files, but the working tree still
# has all the old files from the previous checkout. They're untracked.
# If you don't clean them, `git add -A` on main will re-add everything.
git clean -fd    # Remove ALL untracked files and directories
# OR: explicitly rm -rf the directories you don't want

# 5. Force onto main
git branch -D main
git branch -m main
git push -f origin main
```

## The Pitfall

After `git checkout --orphan`, the index is empty but the **working directory still contains all the old files** as untracked. A subsequent `git add -A` will re-add them all — blowing up what was supposed to be a clean slate with hundreds of unintended files.

**Always run `git clean -fd` after the orphan commit, or explicitly `rm -rf` the directories you want gone.**

## Recovery: If You Already Committed with Too Many Files

If you catch it after the commit but before the push:

```bash
# Undo the commit, unstage everything
git reset --soft HEAD~1       # Commit undone, changes stay staged
git reset HEAD -- .            # Unstage everything
# Now the working tree still has the files, but nothing staged.
# Re-add ONLY what you want:
git add KEEP_THIS.md OTHER_KEEP.md
git commit -m "Corrected commit"

# Clean up leftover untracked files from the old repo
rm -rf old_dirs/ scripts/ tests/   # OR: git clean -fd
```

If you already force-pushed the bad commit, use `git push -f` again after fixing.

## Alternative: Simpler Resets

For simpler cases where you don't need an archive branch:

```bash
# Remove everything except target files, commit
git rm -rf --cached .
git add KEEP_THIS.md
git commit -m "Reset to single file"
git clean -fd
git push -f
```
