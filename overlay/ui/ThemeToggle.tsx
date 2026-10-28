// Dark / light switch. Light mode is the dark theme inverted by CSS (see blake2b-theme.css); the choice is kept in this browser only.
import {useState} from 'react'
import {Moon, Sun} from 'lucide-react'

const KEY = 'bk-theme'

function read(): 'dark' | 'light' {
	return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'
}

export default function ThemeToggle() {
	const [theme, setTheme] = useState<'dark' | 'light'>(read)

	const toggle = () => {
		const next = theme === 'light' ? 'dark' : 'light'
		document.documentElement.setAttribute('data-theme', next)
		try {
			localStorage.setItem(KEY, next)
		} catch {
			/* private mode: the choice just isn't remembered */
		}
		setTheme(next)
	}

	return (
		<button
			type='button'
			onClick={toggle}
			aria-label={theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme'}
			title={theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme'}
			className='b2b-theme-btn'
		>
			{theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
		</button>
	)
}
