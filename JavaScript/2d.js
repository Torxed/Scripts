class _Pos {
	constructor(x, y) {
		this.x = x;
		this.y = y;
	}

	__repr__() {
		return `Pos(x: ${this.x}, y: ${this.y})`
	}
}

class _Tangent {
	constructor(delta) {
		this.delta = delta
	}

	__repr__() {
		return `tan(rad: ${this.radiance}, deg: ${this.angle})`
	}

	get radiance() {
		return Math.atan2(this.delta.y, this.delta.x);
	}

	get angle() {
		return (this.radiance * (180 / Math.PI) + 360) % 360
	}

	get degrees() {
		return this.angle()
	}
}

class _Delta {
	constructor(source, destination) {
		this.source = source
		this.destination = destination
	}

	__repr__() {
		return `Δ(x: ${this.x}, y: ${this.y})`
	}

	get x() {
		return this.destination.x - this.source.x;
	}

	get y() {
		return this.destination.y - this.source.y;
	}

	get distance() {
		return;
	}
}

class _Vector {
	constructor(source, angle) {
		this.source = source
		this.angle = angle
	}

	__repr__() {
		let src = str(this.source)
		return `Vector(source: ${src}, angle: ${this.angle})`
	}

	move(distance) {
		let x_multiplier = Math.cos(((this.angle)/180)*Math.PI)
		let y_multiplier = Math.sin(((this.angle)/180)*Math.PI)

		return new _Pos(this.source.x + (x_multiplier * distance),
						this.source.y + (y_multiplier * distance))
	}
}

class _Distance extends _Delta {
	constructor(source, destination) {
		super(source, destination)
	}

	__repr__() {
		return `Distance(${this.pixels})`
	}

	get pixels() {
		return Math.pow(Math.pow(this.destination.x - this.source.x, 2) + Math.pow(this.destination.y - this.source.y, 2), 0.5)
	}
}

function Pos(x, y) {
	return new _Pos(x, y)
}
function Tangent(delta) {
	return new _Tangent(delta)
}
function Delta(source, destination) {
	return new _Delta(source, destination)
}
function Vector(source, angle) {
	return new _Vector(source, angle)
}
function Distance(source, destination) {
	return new _Distance(source, destination)
}
function str(obj) {
	if (typeof obj.__repr__ !== 'undefined')
		return obj.__repr__()
	return obj
}

window.space = {
	'Pos' : Pos,
	'Tangent' : Tangent,
	'Delta' : Delta,
	'Vector' : Vector,
	'Distance' : Distance,
	'str' : str
}
