class AwesomeList extends React.Component {
	constructor(props) {
		super(props)
	}
	render() {
		return (
			<div id="list_of_awesomeness">
				<ul>
					{(this.props.app.state.items || []).map(item => (
						<li key={item}>{item}</li>
					))}
				</ul>
			</div>
		)
	}
}

class AddButton extends React.Component {
	constructor(props) {
		super(props);
		this.state = {isToggleOn: true};

		// This binding is necessary to make `this` work in the callback
		this.handleClick = this.handleClick.bind(this);
	}

	handleClick() {
		this.props.app.setState(state => ({
			isToggleOn: !state.isToggleOn
		}));
	}

	render() {
		return (
			<button onClick={this.handleClick}>
				{this.state.isToggleOn ? '+' : '-'}
			</button>
		);
	}
}

class DoneButton extends React.Component {
	constructor(props) {
		super(props);
		// This binding is necessary to make `this` work in the callback
		this.handleClick = this.handleClick.bind(this);
	}

	handleClick() {
		let val = document.getElementById('awesomeness').value;
		
		this.props.app.update(this.props.app.state.items.concat(val));
		//this.props.app.setState(val);
	}

	render() {
		return (
			<button onClick={this.handleClick}>
				Done
			</button>
		);
	}
}

function Title() {
	return <h1>You are awesome!</h1>;
}

class AddInput extends React.Component {
	constructor(props) {
		super(props)
	}

	render() {
		return (
			<div id="input_area">
				<input type="text" id="awesomeness" /><br />
				<DoneButton app={this.props.app} /> <button>close</button>
			</div>
		)
	}
}

class App extends React.Component {
	constructor(props) {
		super(props);
		this.state = {
			items: ["Someone said I'm butiful"]
		};
	}

	update(item_list) {
		this.setState({
			items : item_list
		});
		//this.forceUpdate();
		console.log(this.state);
	}

	render() {
		return (
			<div>
				<Title app={this}/>
				<AddButton app={this}/>
				<AddInput app={this}/>
				<AwesomeList app={this}/>
			</div>
		);
	}
}

ReactDOM.render(
	<App />,
	document.getElementById('root')
);
