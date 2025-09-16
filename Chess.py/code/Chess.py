import tkinter as tk
from tkinter import simpledialog, messagebox
from PIL import Image, ImageTk
import copy

DARK_SQUARE_COLOR = "#A66D4F"
LIGHT_SQUARE_COLOR = "#DDB88C"
HIGHLIGHT_MOVE_COLOR = "#5F9EA0"       
HIGHLIGHT_LAST_MOVE_COLOR = "#F5F57E"  
HIGHLIGHT_CHECK_COLOR = "#FF6347"      

class Piece:
    PIECE_VALUES = {"Pawn": 1, "Knight": 3, "Bishop": 3, "Rook": 5, "Queen": 9, "King": 0}

    def __init__(self, color, position):
        self.color = color
        self.position = position
        self.has_moved = False
        self.name = self.__class__.__name__
        self.image_name = f"{color}_{self.name.lower()}"

    def __repr__(self):
        return f"{self.color[0].upper()}{self.name[0]}"

    def get_value(self):
        return self.PIECE_VALUES.get(self.name, 0)

    def get_potential_moves(self, board, for_attack_check=False):
        raise NotImplementedError("Este método deve ser implementado pela subclasse")

class King(Piece):
    def get_potential_moves(self, board, for_attack_check=False):
        moves = []
        row, col = self.position
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0: continue
                new_row, new_col = row + dr, col + dc
                if 0 <= new_row < 8 and 0 <= new_col < 8:
                    target_piece = board.get_piece((new_row, new_col))
                    if target_piece is None or target_piece.color != self.color:
                        moves.append((new_row, new_col))

        if not self.has_moved and not for_attack_check:
            moves.append((row, col + 2)) 
            moves.append((row, col - 2)) 
        return moves

    def _can_castle(self, board, side):
        row, col = self.position
        opponent_color = 'black' if self.color == 'white' else 'white'
        if board.is_square_attacked((row, col), opponent_color):
            return False

        rook_col = 7 if side == 'king_side' else 0
        path_cols = range(col + 1, rook_col) if side == 'king_side' else range(rook_col + 1, col)
        
        rook = board.get_piece((row, rook_col))
        if not isinstance(rook, Rook) or rook.has_moved: return False

        for c in path_cols:
            if board.get_piece((row, c)) is not None: return False
        
        check_cols = [col, col + 1, col + 2] if side == 'king_side' else [col, col - 1, col - 2]
        for c_check in check_cols:
             if 0 <= c_check < 8 and board.is_square_attacked((row, c_check), opponent_color):
                return False
        return True

class Queen(Piece):
    def get_potential_moves(self, board, for_attack_check=False):
        return self._get_sliding_moves(board, Rook.DIRECTIONS + Bishop.DIRECTIONS)

    def _get_sliding_moves(self, board, directions):
        moves = []
        row, col = self.position
        for dr, dc in directions:
            for i in range(1, 8):
                new_row, new_col = row + i * dr, col + i * dc
                if not (0 <= new_row < 8 and 0 <= new_col < 8): break
                
                target_piece = board.get_piece((new_row, new_col))
                if target_piece is None:
                    moves.append((new_row, new_col))
                elif target_piece.color != self.color:
                    moves.append((new_row, new_col))
                    break
                else:
                    break
        return moves

class Rook(Queen):
    DIRECTIONS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    def get_potential_moves(self, board, for_attack_check=False):
        return self._get_sliding_moves(board, self.DIRECTIONS)

class Bishop(Queen):
    DIRECTIONS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    def get_potential_moves(self, board, for_attack_check=False):
        return self._get_sliding_moves(board, self.DIRECTIONS)

class Knight(Piece):
    KNIGHT_MOVES = [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]
    def get_potential_moves(self, board, for_attack_check=False):
        moves = []
        row, col = self.position
        for dr, dc in self.KNIGHT_MOVES:
            new_row, new_col = row + dr, col + dc
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                target_piece = board.get_piece((new_row, new_col))
                if target_piece is None or target_piece.color != self.color:
                    moves.append((new_row, new_col))
        return moves

class Pawn(Piece):
    def get_potential_moves(self, board, for_attack_check=False):
        moves = []
        row, col = self.position
        direction = -1 if self.color == 'white' else 1
        
        if for_attack_check:
            for dc in [-1, 1]:
                if 0 <= row + direction < 8 and 0 <= col + dc < 8:
                    moves.append((row + direction, col + dc))
            return moves

        one_step = (row + direction, col)
        if 0 <= one_step[0] < 8 and board.get_piece(one_step) is None:
            moves.append(one_step)
            if not self.has_moved:
                two_steps = (row + 2 * direction, col)
                if board.get_piece(two_steps) is None:
                    moves.append(two_steps)

        for dc in [-1, 1]:
            capture_pos = (row + direction, col + dc)
            if 0 <= capture_pos[0] < 8 and 0 <= capture_pos[1] < 8:
                target_piece = board.get_piece(capture_pos)
                if target_piece and target_piece.color != self.color:
                    moves.append(capture_pos)
        
        if board.en_passant_target:
            if board.en_passant_target == (row + direction, col - 1) or \
               board.en_passant_target == (row + direction, col + 1):
                moves.append(board.en_passant_target)
        return moves

class Board:
    def __init__(self):
        self.state = [[None for _ in range(8)] for _ in range(8)]
        self.en_passant_target = None
        self.setup_pieces()

    def get_piece(self, position):
        row, col = position
        if 0 <= row < 8 and 0 <= col < 8:
            return self.state[row][col]
        return None

    def move_piece(self, start_pos, end_pos):
        piece = self.get_piece(start_pos)
        captured_piece = self.get_piece(end_pos)
        self.state[end_pos[0]][end_pos[1]] = piece
        self.state[start_pos[0]][start_pos[1]] = None
        if piece:
            piece.position = end_pos
            piece.has_moved = True
        return captured_piece
    
    def is_square_attacked(self, position, attacker_color):
        row, col = position
        
        pawn_dir = 1 if attacker_color == 'white' else -1
        for dc in [-1, 1]:
            piece = self.get_piece((row + pawn_dir, col + dc))
            if isinstance(piece, Pawn) and piece.color == attacker_color:
                return True
        
        for dr, dc in Knight.KNIGHT_MOVES:
            piece = self.get_piece((row + dr, col + dc))
            if isinstance(piece, Knight) and piece.color == attacker_color:
                return True

        for dr_king, dc_king in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
            piece = self.get_piece((row + dr_king, col + dc_king))
            if isinstance(piece, King) and piece.color == attacker_color:
                return True
                
        directions = Rook.DIRECTIONS + Bishop.DIRECTIONS
        for dr, dc in directions:
            for i in range(1, 8):
                check_row, check_col = row + i * dr, col + i * dc
                if not (0 <= check_row < 8 and 0 <= check_col < 8): break
                
                piece = self.get_piece((check_row, check_col))
                if piece:
                    if piece.color == attacker_color:
                        is_rook_or_queen = isinstance(piece, (Rook, Queen))
                        is_bishop_or_queen = isinstance(piece, (Bishop, Queen))
                        if (dr, dc) in Rook.DIRECTIONS and is_rook_or_queen: return True
                        if (dr, dc) in Bishop.DIRECTIONS and is_bishop_or_queen: return True
                    break
        return False

    def setup_pieces(self):
        self.state = [[None for _ in range(8)] for _ in range(8)]
        piece_map = {
            Rook: [(0,0),(0,7),(7,0),(7,7)], Knight: [(0,1),(0,6),(7,1),(7,6)],
            Bishop: [(0,2),(0,5),(7,2),(7,5)], Queen: [(0,3),(7,3)], King: [(0,4),(7,4)]
        }
        for row in [1, 6]:
            color = 'black' if row == 1 else 'white'
            for col in range(8): self.state[row][col] = Pawn(color, (row, col))
        
        for piece_class, positions in piece_map.items():
            for r, c in positions:
                color = 'black' if r < 2 else 'white'
                self.state[r][c] = piece_class(color, (r, c))

class Game:
    def __init__(self, time_control=None):
        self.board = Board()
        self.current_turn = 'white'
        self.game_over = False
        self.winner = None
        self.half_move_clock = 0
        self.position_history = {}
        
        self.time_control = time_control
        self.increment = 0
        
        self.time_left = {}
        if self.time_control:
            base_time, self.increment = self.time_control
            self.time_left = {'white': base_time, 'black': base_time}
        
        self.captured_pieces = {'white': [], 'black': []}
        self.last_move = None
        self.king_in_check_pos = None
        self.move_history = []
        self.move_number = 1

    def play_move(self, start_pos, end_pos):
        piece = self.board.get_piece(start_pos)
        if not piece or piece.color != self.current_turn or self.game_over: return False
        if end_pos not in self.get_legal_moves(piece): return False
        
        captured_piece_for_notation = self.board.get_piece(end_pos)
        is_capture = captured_piece_for_notation is not None or \
                     (isinstance(piece, Pawn) and end_pos == self.board.en_passant_target)
        
        temp_board = copy.deepcopy(self.board)
        temp_board.move_piece(start_pos, end_pos)
        if isinstance(piece, King) and abs(start_pos[1] - end_pos[1]) == 2:
             rook_start_col = 7 if end_pos[1] > start_pos[1] else 0
             rook_end_col = 5 if end_pos[1] > start_pos[1] else 3
             temp_board.move_piece((start_pos[0], rook_start_col), (start_pos[0], rook_end_col))

        temp_game = Game()
        temp_game.board = temp_board
        opponent_color = 'black' if piece.color == 'white' else 'white'
        is_check = temp_game.is_in_check(opponent_color)
        is_checkmate = is_check and not temp_game.get_all_legal_moves_for_color(opponent_color)

        notation = self._get_algebraic_notation(piece, end_pos, is_capture, is_check, is_checkmate)
        self.move_history.append(notation)

        captured_piece = self.board.get_piece(end_pos)
        
        if isinstance(piece, Pawn) or captured_piece is not None:
            self.half_move_clock = 0; self.position_history.clear()
        else:
            self.half_move_clock += 1

        if isinstance(piece, Pawn) and end_pos == self.board.en_passant_target:
            capture_row, capture_col = start_pos[0], end_pos[1]
            en_passant_pawn = self.board.get_piece((capture_row, capture_col))
            if en_passant_pawn: self.captured_pieces[piece.color].append(en_passant_pawn)
            self.board.state[capture_row][capture_col] = None

        self.board.move_piece(start_pos, end_pos)
        self.last_move = (start_pos, end_pos)
        
        if captured_piece:
            self.captured_pieces[self.current_turn].append(captured_piece)
            self.captured_pieces[self.current_turn].sort(key=lambda p: p.get_value(), reverse=True)

        self.board.en_passant_target = ((start_pos[0] + end_pos[0]) // 2, start_pos[1]) if isinstance(piece, Pawn) and abs(start_pos[0] - end_pos[0]) == 2 else None
        
        if isinstance(piece, King) and abs(start_pos[1] - end_pos[1]) == 2:
            rook_start_col, rook_end_col = (7, 5) if end_pos[1] > start_pos[1] else (0, 3)
            self.board.move_piece((start_pos[0], rook_start_col), (start_pos[0], rook_end_col))
        
        if self.time_control:
            self.time_left[self.current_turn] += self.increment
            
        if isinstance(piece, Pawn) and (end_pos[0] == 0 or end_pos[0] == 7):
            return 'promotion'
        
        self._update_game_state()
        return True
    
    def get_material_advantage(self):
        white_score = sum(p.get_value() for p in self.get_all_pieces('white'))
        black_score = sum(p.get_value() for p in self.get_all_pieces('black'))
        diff = white_score - black_score
        if diff != 0: return ('white', diff) if diff > 0 else ('black', -diff)
        return None, 0

    def promote_pawn(self, position, new_piece_class):
        pawn = self.board.get_piece(position)
        if isinstance(pawn, Pawn):
            self.board.state[position[0]][position[1]] = new_piece_class(pawn.color, position)
            
            if self.move_history:
                promoted_piece_symbol = new_piece_class('white', (0,0)).__repr__()[1]
                self.move_history[-1] += f"={promoted_piece_symbol}"

            temp_game = Game(); temp_game.board = self.board
            opponent_color = 'black' if pawn.color == 'white' else 'white'
            is_check = temp_game.is_in_check(opponent_color)
            is_checkmate = is_check and not temp_game.get_all_legal_moves_for_color(opponent_color)

            if is_checkmate and self.move_history: self.move_history[-1] += "#"
            elif is_check and self.move_history: self.move_history[-1] += "+"
            
            self._update_game_state()

    def resign(self):
        if not self.game_over: self.game_over = True; self.winner = f"{'black' if self.current_turn == 'white' else 'white'}_by_resignation"
    def agree_to_draw(self):
        if not self.game_over: self.game_over = True; self.winner = "draw_by_agreement"
    def handle_timeout(self):
        if not self.game_over: self.game_over = True; self.winner = f"{'black' if self.current_turn == 'white' else 'white'}_on_time"
    
    def switch_turn(self):
        self.current_turn = 'black' if self.current_turn == 'white' else 'white'

    def _update_game_state(self):
        if self.current_turn == 'black':
            self.move_number += 1
            
        self.switch_turn()
        king = self.get_king(self.current_turn)
        if king and self.is_in_check(self.current_turn):
            self.king_in_check_pos = king.position
        else:
            self.king_in_check_pos = None

        pos_hash = self.get_position_hash()
        self.position_history[pos_hash] = self.position_history.get(pos_hash, 0) + 1
        
        if not self.get_all_legal_moves_for_color(self.current_turn):
            self.game_over = True
            if self.king_in_check_pos:
                self.winner = 'white' if self.current_turn == 'black' else 'black'
                if self.move_history: self.move_history[-1] = self.move_history[-1].replace('+', '#')
            else:
                self.winner = 'draw_stalemate'
        elif self.half_move_clock >= 100: self.game_over = True; self.winner = 'draw_50_moves'
        elif self.position_history.get(pos_hash, 0) >= 3: self.game_over = True; self.winner = 'draw_repetition'
        elif self.is_insufficient_material(): self.game_over = True; self.winner = 'draw_material'

    def _get_algebraic_notation(self, piece, end_pos, is_capture, is_check, is_checkmate):
        def to_coords(pos): return 'abcdefgh'[pos[1]] + str(8 - pos[0])

        if isinstance(piece, King) and abs(piece.position[1] - end_pos[1]) == 2:
            notation = "O-O" if end_pos[1] > piece.position[1] else "O-O-O"
            if is_checkmate: return notation + "#"
            if is_check: return notation + "+"
            return notation

        #piece_symbol = "" if piece.name == "Pawn" else piece.__repr__()[1]

        if piece.name == "Pawn":
            piece_symbol = ""
        
        elif piece.name == "Knight":
            piece_symbol = "N"

        else:
            piece_symbol = piece.__repr__()[1] 
        
        ambiguity = ""
        if piece.name != "Pawn" and piece.name != "King":
            other_pieces = [p for p in self.get_all_pieces(piece.color) 
                            if isinstance(p, type(piece)) and p.position != piece.position]
            
            for other in other_pieces:
                if end_pos in self.get_legal_moves(other):
                    if other.position[1] != piece.position[1]:
                        ambiguity = to_coords(piece.position)[0]
                    else:
                        ambiguity = to_coords(piece.position)[1]
                    break

        capture_symbol = to_coords(piece.position)[0] + "x" if isinstance(piece, Pawn) and is_capture else "x" if is_capture else ""

        notation = piece_symbol + ambiguity + capture_symbol + to_coords(end_pos)
        
        if is_checkmate: notation += "#"
        elif is_check: notation += "+"
            
        return notation

    def get_all_pieces(self, color):
        return [p for row in self.board.state for p in row if p and p.color == color]

    def get_king(self, color):
        return next((p for p in self.get_all_pieces(color) if isinstance(p, King)), None)

    def is_in_check(self, color):
        king = self.get_king(color)
        return king and self.board.is_square_attacked(king.position, 'black' if color == 'white' else 'white')
    
    def get_legal_moves(self, piece):
        legal_moves = []
        if not piece: return []
        
        for end_pos in piece.get_potential_moves(self.board):
            if isinstance(piece, King) and abs(piece.position[1] - end_pos[1]) == 2:
                if self._is_castle_move_legal(piece, end_pos):
                    legal_moves.append(end_pos)
                continue

            test_board = copy.deepcopy(self.board)
            test_piece = test_board.get_piece(piece.position)
            test_board.move_piece(test_piece.position, end_pos)
            
            temp_game_logic = Game(); temp_game_logic.board = test_board
            if not temp_game_logic.is_in_check(piece.color):
                legal_moves.append(end_pos)
        return legal_moves
    
    def _is_castle_move_legal(self, king, end_pos):
        if king.has_moved: return False
        side = 'king_side' if end_pos[1] > king.position[1] else 'queen_side'
        return king._can_castle(self.board, side)

    def get_all_legal_moves_for_color(self, color):
        return [move for piece in self.get_all_pieces(color) for move in self.get_legal_moves(piece)]

    def get_position_hash(self):
        board_tuple = tuple(tuple(str(p) if p else '.' for p in row) for row in self.board.state)
        full_state_tuple = (board_tuple, self.current_turn, self.board.en_passant_target)
        return hash(full_state_tuple)

    def is_insufficient_material(self):
        pieces = [p for row in self.board.state for p in row if p and p.name != 'King']
        if not pieces: return True
        piece_names = sorted([p.name for p in pieces])
        if piece_names in (['Bishop'], ['Knight']): return True
        if piece_names == ['Bishop', 'Bishop']:
             bishops = [p for p in pieces if p.name == "Bishop"]
             pos1, pos2 = bishops[0].position, bishops[1].position
             if (pos1[0] + pos1[1]) % 2 == (pos2[0] + pos2[1]) % 2: return True
        return False

class ChessGUI(tk.Tk):
    def __init__(self, time_control=None):
        super().__init__()
        self.game = Game(time_control=time_control)
        self.title("Chess")
        self.cell_size = 80
        main_frame = tk.Frame(self); main_frame.pack(padx=10, pady=10)
        self.images, self.small_images = {}, {}; self.load_images()
        self.timer_labels, self.action_buttons, self.captured_widgets = {}, {'white': {}, 'black': {}}, {'white': {}, 'black': {}}
        self._setup_sidebar(main_frame, 'black', tk.LEFT)
        self.canvas = tk.Canvas(main_frame, width=self.cell_size*8, height=self.cell_size*8); self.canvas.pack(side=tk.LEFT)
        self._setup_sidebar(main_frame, 'white', tk.RIGHT)
        self.selected_piece_pos = None
        self.update_displays()
        self.canvas.bind("<Button-1>", self.on_square_click)
        if self.game.time_control: self.after(1000, self.tick_clock)

    def _setup_sidebar(self, parent, color, side):
        sidebar = tk.Frame(parent, width=200); sidebar.pack(side=side, fill=tk.Y, padx=(10,0) if side==tk.RIGHT else (0,10)); sidebar.pack_propagate(False)
        self.timer_labels[color] = tk.Label(sidebar, text="", font=('Arial', 24, 'bold'))
        if self.game.time_control: self.timer_labels[color].pack(pady=10)
        cp_container = tk.Frame(sidebar); cp_container.pack(expand=False, fill=tk.X, pady=10)
        self.captured_widgets[color]['frame'] = tk.Frame(cp_container); self.captured_widgets[color]['frame'].pack()
        self.captured_widgets[color]['advantage_label'] = tk.Label(cp_container, text="", font=('Arial', 10, 'bold')); self.captured_widgets[color]['advantage_label'].pack(side=tk.RIGHT, anchor='n', padx=5)
        if color == 'white': self._setup_move_history(sidebar)
        button_frame = tk.Frame(sidebar); button_frame.pack(side=tk.BOTTOM, pady=20)
        self.action_buttons[color]['draw'] = tk.Button(button_frame, text="Propor Empate", command=self.handle_draw_offer); self.action_buttons[color]['draw'].pack(pady=5)
        self.action_buttons[color]['resign'] = tk.Button(button_frame, text="Desistir", command=self.handle_resign); self.action_buttons[color]['resign'].pack(pady=5)

    def _setup_move_history(self, parent):
        history_frame = tk.LabelFrame(parent, text="Histórico de Jogadas", font=('Arial', 10, 'bold')); history_frame.pack(side=tk.BOTTOM, expand=True, fill='both', pady=10)
        self.move_history_text = tk.Text(history_frame, height=10, width=20, wrap=tk.WORD, font=('Arial', 11))
        scrollbar = tk.Scrollbar(history_frame, command=self.move_history_text.yview); self.move_history_text.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.move_history_text.pack(side=tk.LEFT, expand=True, fill='both', padx=5, pady=5)
        self.move_history_text.tag_configure("move_number", font=('Arial', 11, 'bold')); self.move_history_text.config(state=tk.DISABLED)

    def update_displays(self):
        self.draw_board(); self.update_captured_pieces_display(); self.update_button_states(); self.update_move_history_display()
        if self.game.time_control: self.update_timer_display()

    def update_move_history_display(self):
        self.move_history_text.config(state=tk.NORMAL); self.move_history_text.delete('1.0', tk.END)
        for i in range(0, len(self.game.move_history), 2):
            move_num = (i // 2) + 1
            self.move_history_text.insert(tk.END, f"{move_num}. ", "move_number")
            self.move_history_text.insert(tk.END, f"{self.game.move_history[i]} ")
            if i + 1 < len(self.game.move_history): self.move_history_text.insert(tk.END, f"{self.game.move_history[i+1]}   ")
        self.move_history_text.see(tk.END); self.move_history_text.config(state=tk.DISABLED)

    def update_captured_pieces_display(self):
        for color in ['white', 'black']:
            frame = self.captured_widgets[color]['frame']
            for widget in frame.winfo_children(): widget.destroy()
            opponent = 'black' if color == 'white' else 'white'
            for i, piece in enumerate(self.game.captured_pieces[opponent]):
                img_label = tk.Label(frame, image=self.small_images[piece.image_name], bg=frame.cget('bg')); img_label.grid(row=i // 5, column=i % 5, sticky='w')
        adv_color, adv_points = self.game.get_material_advantage()
        self.captured_widgets['white']['advantage_label'].config(text=f"+{adv_points}" if adv_color == 'white' else "")
        self.captured_widgets['black']['advantage_label'].config(text=f"+{adv_points}" if adv_color == 'black' else "")

    def on_square_click(self, event):
        if self.game.game_over: return
        clicked_pos = (event.y // self.cell_size, event.x // self.cell_size)
        if self.selected_piece_pos:
            result = self.game.play_move(self.selected_piece_pos, clicked_pos)
            self.selected_piece_pos = None
            if result:
                if result == 'promotion': self.prompt_for_promotion(clicked_pos)
                else: self.update_displays()
            self.draw_board()
        else:
            piece = self.game.board.get_piece(clicked_pos)
            if piece and piece.color == self.game.current_turn: self.selected_piece_pos = clicked_pos; self.draw_board()
        if self.game.game_over: self.show_game_over_message()

    def show_game_over_message(self):
        if hasattr(self, '_game_over_message_shown') and self._game_over_message_shown: return
        self._game_over_message_shown = True
        winner_map = {'white_by_resignation':"Pretas desistiram. Brancas vencem!",'black_by_resignation':"Brancas desistiram. Pretas vencem!",'draw_by_agreement':"Empate por acordo.",'white':"Xeque-mate! Brancas vencem!",'black':"Xeque-mate! Pretas vencem!",'white_on_time':"Tempo esgotado! Brancas vencem!", 'black_on_time':"Tempo esgotado! Pretas vencem!",'draw_stalemate':"Empate por Afogamento!",'draw_50_moves':"Empate: regra dos 50 movimentos!",'draw_repetition':"Empate por repetição!",'draw_material':"Empate por material insuficiente!"}
        message = winner_map.get(self.game.winner, "Fim de Jogo!")
        if messagebox.askyesno("Fim de Jogo", f"{message}\nDeseja jogar novamente?"): self.destroy(); main()
        else: self.destroy()

    def load_images(self):
        piece_names = ['white_pawn','white_rook','white_knight','white_bishop','white_queen','white_king','black_pawn','black_rook','black_knight','black_bishop','black_queen','black_king']
        for name in piece_names:
            try:
                image = Image.open(f"assets/{name}.png").convert("RGBA")
                self.images[name] = ImageTk.PhotoImage(image.resize((self.cell_size-10, self.cell_size-10), Image.LANCZOS))
                self.small_images[name] = ImageTk.PhotoImage(image.resize((24, 24), Image.LANCZOS))
            except FileNotFoundError:
                messagebox.showerror("Erro de Arquivo", f"Não foi possível encontrar 'assets/{name}.png'.\nCertifique-se que a pasta 'assets' está no mesmo diretório."); self.destroy(); return

    def update_button_states(self):
        player, opponent = self.game.current_turn, 'black' if self.game.current_turn == 'white' else 'white'
        for btn in self.action_buttons[player].values(): btn.config(state=tk.NORMAL)
        for btn in self.action_buttons[opponent].values(): btn.config(state=tk.DISABLED)

    def handle_draw_offer(self):
        if self.game.game_over: return
        player = "Brancas" if self.game.current_turn == 'white' else 'Pretas'
        if messagebox.askyesno("Proposta de Empate", f"O jogador de peças {player} propõe um empate. Você aceita?"): self.game.agree_to_draw(); self.show_game_over_message()
        else: messagebox.showinfo("Proposta Recusada", "A proposta de empate foi recusada.")

    def handle_resign(self):
        if self.game.game_over: return
        player = "Brancas" if self.game.current_turn == 'white' else 'Pretas'
        if messagebox.askyesno("Confirmar Desistência", f"Você ({player}) tem certeza que deseja desistir?"): self.game.resign(); self.show_game_over_message()

    def tick_clock(self):
        if self.game.game_over: return
        player = self.game.current_turn; self.game.time_left[player] -= 1; self.update_timer_display()
        if self.game.time_left[player] <= 0: self.game.handle_timeout(); self.show_game_over_message()
        else: self.after(1000, self.tick_clock)

    def update_timer_display(self):
        for color, label in self.timer_labels.items():
            time_left = self.game.time_left.get(color, 0)
            minutes, seconds = divmod(max(0, time_left), 60)
            label.config(text=f"{minutes:02d}:{seconds:02d}", fg="green" if color == self.game.current_turn else "black")
    
    def draw_board(self):
        self.canvas.delete("all")
        for r in range(8):
            for c in range(8):
                square_color = LIGHT_SQUARE_COLOR if (r+c)%2==0 else DARK_SQUARE_COLOR
                self.canvas.create_rectangle(c*self.cell_size, r*self.cell_size, (c+1)*self.cell_size, (r+1)*self.cell_size, fill=square_color, outline="")
                text_color = DARK_SQUARE_COLOR if square_color == LIGHT_SQUARE_COLOR else LIGHT_SQUARE_COLOR
                font_size = 10
                if c == 0: self.canvas.create_text(5, r*self.cell_size+5, text=str(8-r), font=('Arial', font_size), fill=text_color, anchor='nw')
                if r == 7: self.canvas.create_text(c*self.cell_size+self.cell_size-5, (r+1)*self.cell_size-5, text='abcdefgh'[c], font=('Arial', font_size), fill=text_color, anchor='se')
        if self.game.last_move:
            start, end = self.game.last_move
            for r, c in [start, end]: self.canvas.create_rectangle(c*self.cell_size, r*self.cell_size, (c+1)*self.cell_size, (r+1)*self.cell_size, fill=HIGHLIGHT_LAST_MOVE_COLOR, outline="", stipple="gray50")
        if self.game.king_in_check_pos:
            r, c = self.game.king_in_check_pos
            self.canvas.create_rectangle(c*self.cell_size, r*self.cell_size, (c+1)*self.cell_size, (r+1)*self.cell_size, fill=HIGHLIGHT_CHECK_COLOR, outline="", stipple="gray50")
        for r in range(8):
            for c in range(8):
                piece = self.game.board.get_piece((r, c))
                if piece: self.canvas.create_image(c*self.cell_size+self.cell_size//2, r*self.cell_size+self.cell_size//2, image=self.images[piece.image_name])
        self.highlight_legal_moves()

    def highlight_legal_moves(self):
        self.canvas.delete("highlight")
        if self.selected_piece_pos:
            selected_piece = self.game.board.get_piece(self.selected_piece_pos)
            if selected_piece:
                for r, c in self.game.get_legal_moves(selected_piece):
                    x0, y0 = c*self.cell_size, r*self.cell_size
                    self.canvas.create_oval(x0+self.cell_size*0.35, y0+self.cell_size*0.35, x0+self.cell_size*0.65, y0+self.cell_size*0.65, fill=HIGHLIGHT_MOVE_COLOR, outline="", tags="highlight")

    def prompt_for_promotion(self, position):
        color = 'black' if self.game.current_turn == 'white' else 'white'
        promo_window = tk.Toplevel(self); promo_window.title("Promoção"); promo_window.transient(self); promo_window.grab_set(); promo_window.protocol("WM_DELETE_WINDOW", lambda: None)
        tk.Label(promo_window, text="Escolha uma peça para promover:").pack(pady=10)
        frame = tk.Frame(promo_window); frame.pack(pady=10)
        promo_pieces = {'q': Queen, 'r': Rook, 'b': Bishop, 'n': Knight}
        def on_promo_choice(p_char):
            self.game.promote_pawn(position, promo_pieces[p_char]); promo_window.destroy(); self.update_displays()
            if self.game.game_over: self.show_game_over_message()
        for p, name in {'q':'queen','r':'rook','b':'bishop','n':'knight'}.items():
            btn = tk.Button(frame, image=self.images[f"{color}_{name}"], command=lambda p_char=p: on_promo_choice(p_char)); btn.pack(side=tk.LEFT, padx=5)

class TimeSetupDialog(simpledialog.Dialog):
    def body(self, master):
        self.title("Configurar Controle de Tempo")
        main_frame = tk.Frame(master); main_frame.pack(padx=20, pady=10)
        base_time_frame = tk.LabelFrame(main_frame, text="Tempo Base", font=('Arial', 10, 'bold')); base_time_frame.pack(fill='x', expand=True, pady=5)
        self.selected_option = tk.StringVar(value="10")
        time_options = [("1 min (Bullet)", "1"), ("3 min (Blitz)", "3"), ("5 min (Blitz)", "5"),("10 min (Rápido)", "10"), ("30 min (Rápido)", "30"), ("90 min (Clássico)", "90"),("Sem Limite", "unlimited")]
        for i, (text, val) in enumerate(time_options):
            rb = tk.Radiobutton(base_time_frame, text=text, variable=self.selected_option, value=val, command=self._on_radio_select); rb.grid(row=i // 2, column=i % 2, sticky='w', padx=10, pady=2)
        custom_frame = tk.Frame(base_time_frame); custom_frame.grid(row=(len(time_options) // 2) + 1, columnspan=2, sticky='w', padx=10)
        self.custom_radio = tk.Radiobutton(custom_frame, text="Personalizado (min):", variable=self.selected_option, value="custom", command=self._on_radio_select); self.custom_radio.pack(side=tk.LEFT)
        self.custom_time_entry = tk.Entry(custom_frame, width=5); self.custom_time_entry.pack(side=tk.LEFT, padx=5); self.custom_time_entry.insert(0, "15")
        self.increment_frame = tk.LabelFrame(main_frame, text="Incremento por Jogada", font=('Arial', 10, 'bold')); self.increment_frame.pack(fill='x', expand=True, pady=(10, 5))
        self.selected_increment = tk.StringVar(value="0")
        increment_options = [("Nenhum", "0"), ("+1 segundo", "1"), ("+3 segundos", "3"), ("+5 segundos", "5")]
        for text, val in increment_options:
            rb = tk.Radiobutton(self.increment_frame, text=text, variable=self.selected_increment, value=val); rb.pack(anchor='w', padx=10)
        self._on_radio_select(); return self.custom_time_entry

    def _on_radio_select(self):
        is_custom = self.selected_option.get() == "custom"; is_unlimited = self.selected_option.get() == "unlimited"
        self.custom_time_entry.config(state=tk.NORMAL if is_custom else tk.DISABLED)
        for child in self.increment_frame.winfo_children(): child.config(state=tk.DISABLED if is_unlimited else tk.NORMAL)

    def apply(self):
        choice = self.selected_option.get()
        if choice == "unlimited": self.result = None; return
        elif choice == "custom":
            try:
                minutes = int(self.custom_time_entry.get())
                if minutes <= 0: messagebox.showerror("Entrada Inválida", "O tempo deve ser maior que zero."); self.result = "invalid"; return
                base_seconds = minutes * 60
            except ValueError: messagebox.showerror("Entrada Inválida", "Por favor, insira um número válido."); self.result = "invalid"; return
        else: base_seconds = int(choice) * 60
        increment_seconds = int(self.selected_increment.get()); self.result = (base_seconds, increment_seconds)

def main():
    root = tk.Tk(); root.withdraw()
    time_setting = "invalid"
    while time_setting == "invalid":
        dialog = TimeSetupDialog(root); time_setting = dialog.result
        if dialog.result is None and time_setting is None: root.destroy(); return
    root.destroy()
    app = ChessGUI(time_control=time_setting)
    app.mainloop()

if __name__ == "__main__":
    main()