// Flat, monochrome latest-blocks strip (replaces the 3D scene). Reads the same data as before.
import {useEffect, useMemo, useState} from 'react'
import {AnimatePresence, motion} from 'framer-motion'
import prettyBytes from 'pretty-bytes'
import prettyMs from 'pretty-ms'

import {useSyncStatus} from '@/hooks/useSyncStatus'
import {useBlocks} from '@/hooks/useBlocks'
import {calcSyncPercent, syncStage} from '@/lib/sync-progress'

import type {Block} from '#types'

const SLOTS = 5
const MAX_WEIGHT = 4_000_000

function ageText(now: number, time: number) {
	const diff = Math.max(0, now - time * 1000)
	return diff < 60_000 ? 'just now' : `${prettyMs(diff, {compact: true, unitCount: 1})} ago`
}

function feeText(p50?: number) {
	if (typeof p50 !== 'number' || !isFinite(p50)) return '—'
	return `${p50 >= 10 ? Math.round(p50) : p50.toFixed(1)} sat/vB`
}

function BlockCard({block, newest, now}: {block: Block; newest: boolean; now: number}) {
	const [copied, setCopied] = useState(false)
	const fill = Math.max(0, Math.min(1, (block.weight ?? 0) / MAX_WEIGHT))

	const copy = () => {
		try {
			void navigator.clipboard?.writeText(block.hash)
			setCopied(true)
			setTimeout(() => setCopied(false), 1200)
		} catch {
			/* clipboard not available */
		}
	}

	return (
		<motion.button
			type='button'
			layout
			initial={{opacity: 0, x: -28}}
			animate={{opacity: 1, x: 0}}
			exit={{opacity: 0, x: 28}}
			transition={{duration: 0.35, ease: 'easeOut'}}
			onClick={copy}
			title={`${block.hash}\nClick to copy the block hash`}
			className={
				'b2b-block flex-1 min-w-0 h-full rounded-[10px] border p-3 text-left flex flex-col justify-between cursor-pointer ' +
				(newest ? 'border-white/45 bg-white/[0.07]' : 'border-white/12 bg-white/[0.03] hover:border-white/30')
			}
		>
			<div>
				<div className='font-mono text-[20px] leading-none tabular-nums text-white'>{block.height?.toLocaleString() ?? '—'}</div>
				<div className='mt-1 text-[12px] text-white/50'>{newest ? 'Latest block' : 'Block'}</div>
			</div>

			<div>
				<div className='h-[3px] w-full rounded-full bg-white/12 overflow-hidden'>
					<div className='h-full rounded-full bg-white/80' style={{width: `${Math.round(fill * 100)}%`}} />
				</div>
				<div className='mt-1 text-[11px] text-white/45'>{Math.round(fill * 100)}% full</div>
			</div>

			<div className='text-[12px] leading-snug text-white/70'>
				<div className='truncate'>{typeof block.txCount === 'number' ? `${block.txCount.toLocaleString()} txs` : '—'}</div>
				<div className='truncate text-white/50'>{feeText(block.feeRates?.p50)}</div>
				<div className='truncate text-white/50'>
					{copied ? 'Hash copied' : `${typeof block.size === 'number' ? prettyBytes(block.size) : '—'} · ${typeof block.time === 'number' ? ageText(now, block.time) : '—'}`}
				</div>
			</div>
		</motion.button>
	)
}

export default function Blocks() {
	const {data: syncStatus} = useSyncStatus()
	const stage = syncStage(syncStatus)
	const {data: rawBlocks = [], isLoading: isLoadingBlocks} = useBlocks({limit: SLOTS, stage})
	// REST returns oldest first; show the newest on the left
	const blocks = useMemo(() => [...rawBlocks].reverse().slice(0, SLOTS), [rawBlocks])

	const [now, setNow] = useState(() => Date.now())
	useEffect(() => {
		const id = setInterval(() => setNow(Date.now()), 15_000)
		return () => clearInterval(id)
	}, [])

	const syncing = stage !== 'synced'

	if (syncing || (isLoadingBlocks && blocks.length === 0)) {
		const pct = calcSyncPercent(syncStatus)
		const have = syncStatus?.blockHeight ?? 0
		const want = syncStatus?.validatedHeaderHeight ?? 0
		const title =
			stage === 'pre-headers'
				? 'Pre-synchronizing block headers'
				: stage === 'headers'
					? 'Synchronizing block headers'
					: stage === 'IBD'
						? 'Downloading and verifying blocks'
						: 'Loading blocks'
		return (
			<div className='w-[768px] max-w-full h-[180px]'>
				<div className='h-full rounded-[10px] border border-white/12 bg-white/[0.03] p-5 flex flex-col justify-between'>
					<div>
						<div className='text-[18px] text-white'>{title}</div>
						<div className='mt-1 font-mono text-[13px] text-white/55 tabular-nums'>
							{want > 0 ? `${have.toLocaleString()} of ${want.toLocaleString()} blocks` : 'waiting for peers…'}
						</div>
					</div>
					<div>
						<div className='h-[6px] w-full rounded-full bg-white/12 overflow-hidden'>
							<div className='h-full rounded-full bg-white/85 transition-[width] duration-700' style={{width: `${Math.min(100, pct)}%`}} />
						</div>
						<div className='mt-2 text-[12px] text-white/50 tabular-nums'>{pct.toFixed(2)}%</div>
					</div>
				</div>
			</div>
		)
	}

	return (
		<div className='w-[768px] max-w-full h-[180px] flex gap-3'>
			<AnimatePresence mode='popLayout' initial={false}>
				{blocks.map((block, i) => (
					<BlockCard key={block.hash} block={block} newest={i === 0} now={now} />
				))}
			</AnimatePresence>
		</div>
	)
}
